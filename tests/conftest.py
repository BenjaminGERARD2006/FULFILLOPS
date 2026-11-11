
import pytest
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.seed import seed_catalog


@pytest.fixture(scope="session")
def test_database_guard():
    if settings.POSTGRES_DB != "fulfillops_test":
        pytest.exit(
            "SAFETY STOP: Tests require POSTGRES_DB=fulfillops_test. "
            "Set this environment variable before running pytest.",
            returncode=2,
        )


def reset_test_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    jobs,
                    idempotency_records,
                    order_items,
                    orders,
                    inventory,
                    products
                RESTART IDENTITY CASCADE
                """
            )
        )

    seed_catalog()


@pytest.fixture(autouse=True)
def clean_test_database(test_database_guard):
    # Start each test with the original catalog and stock.
    reset_test_database()

    yield

    # Restore the isolated test dataset after each test.
    reset_test_database()
