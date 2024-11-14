import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


def pytest_configure(config):
    """Configure pytest options"""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )

    # Set asyncio mode via pytest.ini settings
    config.inicfg['asyncio_mode'] = 'auto'


# Configure asyncio plugin defaults
pytest_plugins = ["pytest_asyncio"]
