"""Pytest configuration and fixtures."""

import os
import pytest
from dotenv import load_dotenv

# Load .env at import time for pytest
load_dotenv()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(scope="session")
def openai_api_available():
    """Check if OpenAI API is available for testing."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return bool(api_key) and not api_key.startswith("sk-your")


@pytest.fixture(scope="session")
def test_url():
    """Get test URL from environment."""
    return os.getenv("TEST_URL", "https://www.piaotia.com/html/8/8717/index.html")


@pytest.fixture(scope="session")
def test_chapters():
    """Get test chapters range from environment."""
    return os.getenv("TEST_CHAPTERS", "1-10")
