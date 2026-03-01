"""Streaming pipeline for concurrent crawl + translate with resume support."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import structlog
from pydantic import BaseModel

from dich_truyen.config import PipelineConfig, get_config
from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus

if TYPE_CHECKING:
    from dich_truyen.crawler.downloader import ChapterDownloader
    from dich_truyen.translator.engine import TranslationEngine
    from dich_truyen.translator.glossary import Glossary

logger = structlog.get_logger()


class PipelineResult(BaseModel):
    """Result of streaming pipeline execution."""

    total_chapters: int = 0
    crawled: int = 0
    translated: int = 0
    skipped_crawl: int = 0
    skipped_translate: int = 0
    failed_crawl: int = 0
    failed_translate: int = 0
    errors: list[str] = []
    cancelled: bool = False  # True if user pressed Ctrl+C
    all_done: bool = False  # True if all chapters in range are translated


@dataclass
class PipelineStats:
    """Mutable stats for progress tracking."""

    total_chapters: int = 0
    chapters_crawled: int = 0
    chapters_translated: int = 0
    chunks_translated: int = 0
    total_chunks: int = 0
    chapters_in_queue: int = 0
    crawl_errors: int = 0
    translate_errors: int = 0
    errors: list[str] = field(default_factory=list)
    # Worker status tracking: {worker_id: "Ch.1: [1,2,3]"}
    worker_status: dict = field(default_factory=dict)
    # Crawl status: "Ch.5: 第五章..."
    crawl_status: str = ""
    # General status message (shown in table footer)
    status_message: str = ""
    # Glossary count
    glossary_count: int = 0


class StreamingPipeline:
    """Concurrent crawl + translate pipeline with resume support.

    Uses producer-consumer pattern:
    - Crawler (producer): Downloads chapters and puts them in queue
    - Translators (consumers): Take chapters from queue and translate

    Thread safety:
    - _progress_lock: Protects BookProgress updates
    - _glossary_lock: Protects Glossary modifications
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        translator_workers: Optional[int] = None,
    ):
        """Initialize the streaming pipeline.

        Args:
            config: Pipeline configuration
            translator_workers: Override number of translator workers
        """
        self.config = config or get_config().pipeline
        self.num_workers = translator_workers or self.config.translator_workers

        # Shared state - unbounded queue so crawler never blocks
        # Resume works because chapter status is saved to disk after each operation
        self.queue: asyncio.Queue[Chapter | None] = asyncio.Queue()  # maxsize=0 (unbounded)
        self.progress: Optional[BookProgress] = None
        self.book_dir: Optional[Path] = None
        self.stats = PipelineStats()

        # Thread safety locks
        self._progress_lock = asyncio.Lock()
        self._glossary_lock = asyncio.Lock()

        # Components (set during run)
        self.downloader: Optional["ChapterDownloader"] = None
        self.engine: Optional["TranslationEngine"] = None
        self.glossary: Optional["Glossary"] = None
        self.style = None  # StyleTemplate for glossary generation

        # Control flags
        self._crawl_complete = asyncio.Event()
        self._stop_requested = False
        self._glossary_generated = False  # Track if glossary has been generated
        self._auto_glossary = True  # Whether to auto-generate glossary

        # Solution 4: Glossary sync
        self._glossary_ready_event = asyncio.Event()  # Signal when glossary is ready
        self._glossary_version = 0  # Increment when glossary changes
        self._pending_extraction_paths: list[Path] = []  # Queued for batch extraction
        self._last_scorer_rebuild_version = 0  # Track last TF-IDF rebuild

        # Graceful shutdown
        self._shutdown_event = asyncio.Event()  # Signal for coordinated shutdown
        self._cancelled = False  # Track if cancelled by user

    async def run(
        self,
        book_dir: Path,
        url: Optional[str] = None,
        chapters_spec: Optional[str] = None,
        style_name: str = "tien_hiep",
        auto_glossary: bool = True,
        force: bool = False,
        crawl_only: bool = False,
        translate_only: bool = False,
    ) -> PipelineResult:
        """Run the streaming pipeline.

        Args:
            book_dir: Book directory path
            url: Book index URL (required for new books)
            chapters_spec: Optional chapter range (e.g., "1-100")
            style_name: Translation style name
            auto_glossary: Whether to auto-generate glossary
            force: Force re-process all chapters
            crawl_only: Stop after crawl phase (no translation)

        Returns:
            PipelineResult with statistics
        """
        from dich_truyen.crawler.downloader import ChapterDownloader
        from dich_truyen.translator.engine import setup_translation
        from dich_truyen.utils.progress import parse_chapter_range

        self.book_dir = Path(book_dir)
        self.book_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or load book progress
        if url:
            self.downloader = ChapterDownloader(self.book_dir)
            self.progress = await self.downloader.initialize_book(url)
        else:
            self.progress = BookProgress.load(self.book_dir)
            if not self.progress:
                raise ValueError("No book.json found. Provide --url for new books.")
            self.downloader = ChapterDownloader(self.book_dir)
            self.downloader.progress = self.progress

        # Parse chapter range
        all_chapters = self.progress.chapters
        if chapters_spec:
            indices = set(parse_chapter_range(chapters_spec, len(all_chapters)))
            chapters = [c for c in all_chapters if c.index in indices]
        else:
            chapters = all_chapters

        self.stats.total_chapters = len(chapters)

        # Analyze state for resume
        if force:
            # Determine reset target based on mode:
            # - translate_only: reset to CRAWLED (force re-translate, skip crawl)
            # - crawl_only: reset to PENDING (force re-crawl everything)
            # - default: CRAWLED if no URL (re-translate only), PENDING if URL (re-crawl + re-translate)
            if translate_only:
                reset_to = ChapterStatus.CRAWLED
            elif crawl_only:
                reset_to = ChapterStatus.PENDING
            else:
                reset_to = ChapterStatus.CRAWLED if url is None else ChapterStatus.PENDING
            for c in chapters:
                # Only reset if raw file exists when targeting CRAWLED
                if reset_to == ChapterStatus.CRAWLED:
                    raw_files = list((self.book_dir / "raw").glob(f"{c.index:04d}_*.txt"))
                    if raw_files:
                        c.status = ChapterStatus.CRAWLED
                    # If no raw file, leave as PENDING (needs crawl)
                else:
                    c.status = ChapterStatus.PENDING
            self.progress.save(self.book_dir)

        to_crawl = (
            [] if translate_only else [c for c in chapters if c.status == ChapterStatus.PENDING]
        )
        to_translate = [
            c for c in chapters if c.status in (ChapterStatus.CRAWLED, ChapterStatus.ERROR)
        ]
        already_done = [c for c in chapters if c.status == ChapterStatus.TRANSLATED]

        # Log LLM configuration summary
        from dich_truyen.config import log_llm_config_summary

        log_llm_config_summary()

        logger.info(
            "pipeline_start",
            book=self.progress.title,
            book_vi=self.progress.title_vi or "translating...",
            total=len(chapters),
            to_crawl=len(to_crawl),
            to_translate=len(to_translate),
            already_done=len(already_done),
        )

        # Check if anything to do
        if not to_crawl and not to_translate:
            logger.info("pipeline_all_done")
            return PipelineResult(
                total_chapters=len(chapters),
                skipped_crawl=len(chapters),
                skipped_translate=len(chapters),
                all_done=True,
            )

        logger.debug("setting_up_engine")

        # Check if raw files already exist for glossary generation
        raw_dir = self.book_dir / "raw"
        has_raw_files = raw_dir.exists() and any(raw_dir.glob("*.txt"))

        # Save auto_glossary setting - if no raw files yet but we're crawling,
        # we'll generate glossary after crawl completes
        self._auto_glossary = auto_glossary
        self._glossary_generated = has_raw_files  # Already generated if raw files existed

        self.engine = await setup_translation(
            book_dir=self.book_dir,
            style_name=style_name,
            auto_glossary=auto_glossary and has_raw_files,  # Only generate NOW if raw files exist
        )
        self.glossary = self.engine.glossary
        self.style = self.engine.style  # Capture style for glossary generation

        # Reload progress to get translated metadata (setup_translation updates it)
        self.progress = BookProgress.load(self.book_dir)

        # Rebuild chapter lists from reloaded progress to maintain object references
        all_chapters = self.progress.chapters
        if chapters_spec:
            indices = set(parse_chapter_range(chapters_spec, len(all_chapters)))
            chapters = [c for c in all_chapters if c.index in indices]
        else:
            chapters = all_chapters

        to_crawl = (
            [] if translate_only else [c for c in chapters if c.status == ChapterStatus.PENDING]
        )
        to_translate = [
            c for c in chapters if c.status in (ChapterStatus.CRAWLED, ChapterStatus.ERROR)
        ]

        # Handle crawl_only mode - skip translation setup and workers
        if crawl_only:
            logger.info("crawl_only_mode", to_crawl=len(to_crawl))

            if not to_crawl:
                logger.info("all_chapters_crawled")
                return PipelineResult(
                    total_chapters=len(chapters),
                    crawled=0,
                    translated=0,
                    skipped_crawl=len(chapters),
                    skipped_translate=len(chapters),
                )

            # Just run crawler, no translation
            self.stats.total_chapters = len(to_crawl)
            await self._crawl_producer(to_crawl)

            logger.info(
                "crawl_complete",
                crawled=self.stats.chapters_crawled,
                errors=self.stats.crawl_errors,
            )

            return PipelineResult(
                total_chapters=len(chapters),
                crawled=self.stats.chapters_crawled,
                translated=0,
                skipped_crawl=len(chapters) - len(to_crawl),
                skipped_translate=len(chapters),
                failed_crawl=self.stats.crawl_errors,
                errors=self.stats.errors,
            )

        logger.debug("starting_workers", workers=self.num_workers)

        # Create tasks
        tasks = []

        # Crawler task (only if there are chapters to crawl)
        if to_crawl:
            tasks.append(asyncio.create_task(self._crawl_producer(to_crawl), name="crawler"))
        else:
            # No crawling needed, signal completion
            self._crawl_complete.set()

        # Translator tasks (start these BEFORE pre-queuing to avoid deadlock)
        for i in range(self.num_workers):
            tasks.append(
                asyncio.create_task(self._translate_consumer(i + 1), name=f"translator-{i + 1}")
            )

        # Batch extraction background task (Solution 4) - managed separately
        batch_extraction_task = None
        if self.engine and self.engine.config.progressive_glossary:
            batch_extraction_task = asyncio.create_task(
                self._batch_extraction_task(), name="batch-extraction"
            )

        # Pre-queue already crawled chapters (now safe because consumers are running)
        async def pre_queue_chapters():
            for chapter in to_translate:
                await self.queue.put(chapter)
                self.stats.chapters_in_queue += 1

            # If no crawler running, we need to send poison pills after pre-queuing
            # Otherwise, the crawler's finally block will send them
            if not to_crawl:
                for _ in range(self.num_workers):
                    await self.queue.put(None)  # Poison pill

        # Start pre-queuing as a task
        if to_translate:
            tasks.append(asyncio.create_task(pre_queue_chapters(), name="pre-queue"))
        elif not to_crawl:
            # No chapters to crawl or translate, just send poison pills
            async def send_poison_pills():
                for _ in range(self.num_workers):
                    await self.queue.put(None)

            tasks.append(asyncio.create_task(send_poison_pills(), name="poison-pills"))

        try:
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.warning("pipeline_shutdown_requested")
                self._shutdown_event.set()
                self._cancelled = True

                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), timeout=30
                    )
                except asyncio.TimeoutError:
                    logger.warning("pipeline_shutdown_timeout")
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                self._stop_requested = True

        except Exception as e:
            logger.error("pipeline_error", error=str(e))
            self._cancelled = True

        finally:
            # Signal shutdown to stop batch extraction task
            self._shutdown_event.set()

            # Cancel and wait for batch extraction task
            if batch_extraction_task is not None:
                batch_extraction_task.cancel()
                try:
                    await batch_extraction_task
                except asyncio.CancelledError:
                    pass

            # Always save state on exit (normal, cancelled, or error)
            if self.glossary and len(self.glossary) > 0:
                self.glossary.save(self.book_dir)
            if self.progress:
                self.progress.save(self.book_dir)

        # Determine if all chapters in range are done
        total_target = len(to_crawl) + len(to_translate)
        all_translated = self.stats.chapters_translated >= total_target
        was_cancelled = self._cancelled

        logger.info(
            "pipeline_complete" if not was_cancelled else "pipeline_interrupted",
            crawled=self.stats.chapters_crawled,
            translated=self.stats.chapters_translated,
            crawl_errors=self.stats.crawl_errors,
            translate_errors=self.stats.translate_errors,
            glossary_entries=len(self.glossary) if self.glossary else 0,
        )

        return PipelineResult(
            total_chapters=self.stats.total_chapters,
            crawled=self.stats.chapters_crawled,
            translated=self.stats.chapters_translated,
            skipped_crawl=len(already_done) + len(to_translate),
            skipped_translate=len(already_done),
            failed_crawl=self.stats.crawl_errors,
            failed_translate=self.stats.translate_errors,
            errors=self.stats.errors,
            cancelled=was_cancelled,
            all_done=all_translated and not was_cancelled,
        )

    async def _crawl_producer(self, chapters: list[Chapter]) -> None:
        """Download chapters and put into queue.

        Args:
            chapters: Chapters to download (PENDING status)
        """
        from dich_truyen.crawler.base import BaseCrawler
        from dich_truyen.crawler.downloader import slugify
        from dich_truyen.crawler.pattern import PatternDiscovery

        raw_dir = self.book_dir / "raw"
        raw_dir.mkdir(exist_ok=True)

        discovery = PatternDiscovery()

        try:
            async with BaseCrawler(self.downloader.config) as crawler:
                for chapter in chapters:
                    if self._stop_requested or self._shutdown_event.is_set():
                        break

                    try:
                        # Update crawl status
                        title_preview = (chapter.title_cn or "")[:15]
                        self.stats.crawl_status = f"Ch.{chapter.index}: {title_preview}..."

                        # Fetch chapter page
                        html = await crawler.fetch(chapter.url, self.progress.encoding)

                        # Extract content
                        title, content = discovery.extract_chapter_content(
                            html, self.progress.patterns
                        )

                        # Update title if extracted
                        if title and not chapter.title_cn:
                            chapter.title_cn = title

                        # Save to file
                        filename = f"{chapter.index:04d}_{slugify(chapter.title_cn)}.txt"
                        filepath = raw_dir / filename

                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"# {chapter.title_cn}\n\n")
                            f.write(content)

                        # Update status safely
                        await self._update_chapter_status(chapter, ChapterStatus.CRAWLED)
                        self.stats.chapters_crawled += 1
                        logger.info(
                            "chapter_crawled",
                            chapter=chapter.index,
                            title=chapter.title_cn or "",
                        )

                        # Put in queue for translation
                        await self.queue.put(chapter)
                        self.stats.chapters_in_queue += 1

                    except Exception as e:
                        error_msg = f"Crawl chapter {chapter.index}: {str(e)}"
                        self.stats.errors.append(error_msg)
                        self.stats.crawl_errors += 1
                        logger.error("chapter_crawl_error", chapter=chapter.index, error=str(e))
                        await self._update_chapter_status(chapter, ChapterStatus.ERROR, str(e))

                    # Rate limiting
                    await asyncio.sleep(self.config.crawl_delay_ms / 1000)

        finally:
            # Signal completion to all workers
            self._crawl_complete.set()
            for _ in range(self.num_workers):
                await self.queue.put(None)  # Poison pill

    async def _translate_consumer(self, worker_id: int) -> None:
        """Take chapters from queue and translate.

        Args:
            worker_id: Worker identifier for logging
        """
        translated_dir = self.book_dir / "translated"
        translated_dir.mkdir(exist_ok=True)
        raw_dir = self.book_dir / "raw"

        # Initialize worker status
        self.stats.worker_status[worker_id] = "idle"

        while True:
            # Wait for chapter from queue
            chapter = await self.queue.get()

            # Check for poison pill or shutdown
            if chapter is None or self._shutdown_event.is_set():
                self.stats.worker_status[worker_id] = "done"
                break

            self.stats.chapters_in_queue -= 1

            # Skip if already translated
            if chapter.status == ChapterStatus.TRANSLATED:
                continue

            # Generate glossary if needed (first worker to reach this generates)
            await self._generate_glossary_if_needed()

            try:
                # Find source file
                source_files = list(raw_dir.glob(f"{chapter.index:04d}_*.txt"))
                if not source_files:
                    raise FileNotFoundError(f"No raw file for chapter {chapter.index}")

                source_path = source_files[0]
                output_path = translated_dir / f"{chapter.index}.txt"

                # Create progress callback for chunk-level updates
                chapter_title = (chapter.title_cn or "")[:15]
                logger.info(
                    "chapter_translating",
                    worker=worker_id,
                    chapter=chapter.index,
                    title=chapter_title,
                )

                def progress_callback(completed_count, total_chunks, status=""):
                    # status from engine: "translating [1,2]" or "[done]" or "[1,2]"
                    # Show: "Ch.5: 章节标题... 2/5 [1,2]"
                    progress_str = f"{completed_count}/{total_chunks}"
                    self.stats.worker_status[worker_id] = (
                        f"Ch.{chapter.index}: {chapter_title}... {progress_str} {status}"
                    )
                    # Track total chunks on first callback only
                    if completed_count == 0 and "translating" in status:
                        self.stats.total_chunks += total_chunks
                    # Track chunk completion only when done (not when starting)
                    if "done" in status or (completed_count > 0 and "translating" not in status):
                        pass  # Don't double count - chunks_translated updated below

                # Translate chapter with progress callback
                await self.engine.translate_chapter(source_path, output_path, progress_callback)

                # Update final status
                self.stats.worker_status[worker_id] = f"Ch.{chapter.index}: done"

                # Translate chapter title if needed
                if chapter.title_cn and not chapter.title_vi:
                    chapter.title_vi = await self.engine.llm.translate_title(
                        chapter.title_cn, "chapter"
                    )

                # Queue for batched progressive glossary (Solution 4)
                if self.engine.config.progressive_glossary and self.glossary:
                    self._pending_extraction_paths.append(source_path)

                # Update status safely
                await self._update_chapter_status(chapter, ChapterStatus.TRANSLATED)
                self.stats.chapters_translated += 1
                logger.info(
                    "chapter_translated",
                    worker=worker_id,
                    chapter=chapter.index,
                    title=chapter.title_vi or chapter.title_cn or "",
                )

            except Exception as e:
                error_msg = f"Translate chapter {chapter.index}: {str(e)}"
                self.stats.errors.append(error_msg)
                self.stats.translate_errors += 1
                logger.error(
                    "chapter_translate_error",
                    worker=worker_id,
                    chapter=chapter.index,
                    error=str(e),
                )
                await self._update_chapter_status(chapter, ChapterStatus.ERROR, str(e))

    async def _update_chapter_status(
        self,
        chapter: Chapter,
        status: ChapterStatus,
        error: Optional[str] = None,
    ) -> None:
        """Thread-safe chapter status update.

        Args:
            chapter: Chapter to update
            status: New status
            error: Optional error message
        """
        async with self._progress_lock:
            self.progress.update_chapter_status(chapter.index, status, error)
            self.progress.save(self.book_dir)

    async def _extract_progressive_glossary(self, source_path: Path) -> None:
        """Thread-safe progressive glossary extraction.

        Extracts new terms from a chapter and adds them to the shared glossary.
        All workers share the same Glossary object reference, so updates are
        immediately visible to other workers.

        Thread Safety:
            - Uses _glossary_lock for concurrent add operations
            - Python's GIL ensures list/dict operations are atomic
            - New terms are available to subsequent translations

        Limitations:
            - TF-IDF scorer is not updated, so new terms may not be optimally ranked
            - Terms added during a translation won't be used in that translation
            - These are acceptable tradeoffs for simplicity

        Args:
            source_path: Path to source chapter file
        """
        from dich_truyen.translator.glossary import extract_new_terms_from_chapter

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                chapter_content = f.read()

            new_terms = await extract_new_terms_from_chapter(
                chapter_content, self.glossary, style=self.style, max_new_terms=3
            )

            if new_terms:
                async with self._glossary_lock:
                    for term in new_terms:
                        self.glossary.add(term)
                    self.glossary.save(self.book_dir)
                    self.stats.glossary_count = len(self.glossary)

        except Exception:
            # Non-blocking, just skip progressive glossary on error
            pass

    async def _generate_glossary_if_needed(self) -> None:
        """Generate glossary from raw files if not already done.

        Called by first translation worker after crawl completes.
        Thread-safe - only one worker will generate.

        Solution 4 fix: Sets _glossary_generated flag AFTER successful completion,
        not before. This allows another worker to retry if generation fails.
        """
        from dich_truyen.translator.glossary import Glossary, generate_glossary_from_samples

        # Quick check without lock
        if self._glossary_generated or not self._auto_glossary:
            return

        async with self._glossary_lock:
            # Double-check after acquiring lock
            if self._glossary_generated:
                return

            # Check if glossary already has entries
            if self.glossary and len(self.glossary) > 0:
                self._glossary_generated = True
                self._glossary_version = 1
                self._glossary_ready_event.set()
                logger.debug("glossary_already_populated", entries=len(self.glossary))
                return

            # Check for raw files
            raw_dir = self.book_dir / "raw"
            if not raw_dir.exists():
                self._glossary_generated = True  # Nothing to generate from
                self._glossary_ready_event.set()
                return

            all_files = sorted(raw_dir.glob("*.txt"))
            if not all_files:
                self._glossary_generated = True
                self._glossary_ready_event.set()
                return

            logger.info("generating_glossary_from_crawled")

            try:
                # Get config values
                config = get_config().translation
                sample_chapter_count = config.glossary_sample_chapters
                sample_size = config.glossary_sample_size
                random_sample = config.glossary_random_sample
                min_entries = config.glossary_min_entries
                max_entries = config.glossary_max_entries

                # Sample from available files
                import random

                if len(all_files) > sample_chapter_count:
                    if random_sample:
                        sample_files = random.sample(all_files, sample_chapter_count)
                    else:
                        sample_files = all_files[:sample_chapter_count]
                else:
                    sample_files = all_files

                # Read samples
                samples = []
                for f in sample_files:
                    try:
                        content = f.read_text(encoding="utf-8")
                        samples.append(content[:sample_size])
                    except Exception:
                        pass

                if samples:
                    # Create glossary if needed
                    if not self.glossary:
                        self.glossary = Glossary.load_or_create(self.book_dir)
                        self.engine.glossary = self.glossary

                    # Generate
                    self.glossary = await generate_glossary_from_samples(
                        samples,
                        style=self.style,
                        existing_glossary=self.glossary,
                        min_entries=min_entries,
                        max_entries=max_entries,
                    )
                    self.glossary.save(self.book_dir)
                    self.engine.glossary = self.glossary

                    # Update stats for Live display
                    self.stats.glossary_count = len(self.glossary)
                    self.stats.status_message = "Glossary generated"

                # SUCCESS: Now set the flag and signal (Solution 4 fix)
                self._glossary_generated = True
                self._glossary_version = 1
                self._glossary_ready_event.set()

            except Exception as e:
                # FAILURE: Don't set flag - let another worker retry
                logger.error("glossary_generation_failed", error=str(e))
                logger.warning("glossary_will_retry")
                # Don't set self._glossary_generated = True

    async def _wait_for_glossary_or_shutdown(self) -> bool:
        """Wait for either glossary ready or shutdown signal.

        Returns:
            True if glossary is ready, False if shutdown requested
        """
        glossary_task = asyncio.create_task(self._glossary_ready_event.wait())
        shutdown_task = asyncio.create_task(self._shutdown_event.wait())

        done, pending = await asyncio.wait(
            [glossary_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Return True if glossary ready, False if shutdown
        return glossary_task in done

    async def _run_batch_extraction(self) -> None:
        """Extract terms from pending chapters in one batch.

        Called periodically by batch extraction task.
        Single version increment per batch to reduce sync overhead.
        """
        from dich_truyen.translator.glossary import extract_new_terms_from_chapter

        async with self._glossary_lock:
            if not self._pending_extraction_paths or not self.glossary:
                return

            paths_to_process = self._pending_extraction_paths.copy()
            self._pending_extraction_paths.clear()

        # Process outside lock to reduce contention
        all_new_terms = []
        for path in paths_to_process:
            try:
                content = path.read_text(encoding="utf-8")
                terms = await extract_new_terms_from_chapter(
                    content, self.glossary, max_new_terms=3
                )
                all_new_terms.extend(terms)
            except Exception:
                pass  # Skip errors, non-blocking

        if not all_new_terms:
            return

        # Deduplicate and add under lock
        async with self._glossary_lock:
            added_count = 0
            seen = set()
            for term in all_new_terms:
                if term.chinese not in seen and term.chinese not in self.glossary:
                    self.glossary.add(term)
                    seen.add(term.chinese)
                    added_count += 1

            if added_count > 0:
                self._glossary_version += 1
                self.glossary.save(self.book_dir)
                self.stats.glossary_count = len(self.glossary)
                self.stats.status_message = f"+{added_count} terms extracted"

                # Rebuild TF-IDF scorer periodically
                await self._maybe_rebuild_scorer()

    async def _maybe_rebuild_scorer(self) -> None:
        """Rebuild TF-IDF scorer if version threshold reached."""
        version_delta = self._glossary_version - self._last_scorer_rebuild_version
        if version_delta < self.config.glossary_scorer_rebuild_threshold:
            return

        if not self.engine or not self.glossary:
            return

        raw_dir = self.book_dir / "raw"
        if not raw_dir.exists():
            return

        try:
            from dich_truyen.translator.term_scorer import SimpleTermScorer

            documents = []
            for txt_file in sorted(raw_dir.glob("*.txt")):
                try:
                    documents.append(txt_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            if documents:
                terms = [entry.chinese for entry in self.glossary.entries]
                new_scorer = SimpleTermScorer()
                new_scorer.fit(documents, terms)
                self.engine.term_scorer = new_scorer
                self._last_scorer_rebuild_version = self._glossary_version
        except Exception:
            pass  # Non-blocking, scorer update is optional

    async def _batch_extraction_task(self) -> None:
        """Background task: batch extract terms periodically.

        Runs every glossary_batch_interval seconds.
        Stops when shutdown event is set.
        """
        while not self._shutdown_event.is_set():
            try:
                # Wait for interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self.config.glossary_batch_interval
                )
                break  # Shutdown requested
            except asyncio.TimeoutError:
                pass  # Normal timeout, run extraction

            await self._run_batch_extraction()

        # Final flush on shutdown
        await self._run_batch_extraction()
