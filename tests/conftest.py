"""Pytest test configuration and fixtures."""
import os
import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app
from src.config import settings
from src.database import get_db, init_db

# Ensure test settings
os.environ["SIMULATION_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_incubrix.db"


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    yield
    # Cleanup test db file after session if desired
    db_file = "test_incubrix.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
