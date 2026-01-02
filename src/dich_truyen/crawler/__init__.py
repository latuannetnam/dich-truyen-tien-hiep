"""Crawler module for downloading chapters from Chinese novel websites."""

from dich_truyen.crawler.base import BaseCrawler
from dich_truyen.crawler.downloader import ChapterDownloader
from dich_truyen.crawler.pattern import PatternDiscovery

__all__ = ["BaseCrawler", "ChapterDownloader", "PatternDiscovery"]
