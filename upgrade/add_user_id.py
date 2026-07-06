import glob
import logging
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

# Add parent directory to path so we can import from the project
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

# Load environment variables from .env file
dotenv_path = os.path.join(parent_dir, ".env")
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_database_urls():
    """
    Resolve database URLs to process.
    - If DATABASE_URL is set: use it (PostgreSQL or explicit SQLite)
    - If not set: scan /app/db and project root for all .db files
    Returns a list of database URLs.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        logger.info(f"Using database from DATABASE_URL: {url}")
        return [url]

    # Fallback: scan for all SQLite .db files
    logger.warning("DATABASE_URL not set, scanning for SQLite .db files...")
    urls = []

    search_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db"),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ]

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        db_files = glob.glob(os.path.join(directory, "*.db"))
        for db_file in db_files:
            sqlite_url = f"sqlite:///{db_file}"
            if sqlite_url not in urls:
                logger.info(f"Found SQLite database: {db_file}")
                urls.append(sqlite_url)

    if not urls:
        logger.warning("No SQLite database files found and DATABASE_URL is not set.")

    return urls


def add_user_id_column():
    """Add user_id column to the auth table across all discovered databases."""
    logger.info("Starting to add user_id column to auth table")

    database_urls = get_database_urls()

    if not database_urls:
        logger.error("No databases to process. Exiting.")
        return False

    results = {}
    for url in database_urls:
        label = url.split("///")[-1] if "sqlite" in url else url.split("@")[-1]
        logger.info(f"Processing: {label}")
        results[url] = _add_column_to_database(url)

    # Summary
    succeeded = [u for u, ok in results.items() if ok]
    failed = [u for u, ok in results.items() if not ok]

    logger.info(f"Completed: {len(succeeded)} succeeded, {len(failed)} failed")
    if failed:
        for url in failed:
            logger.error(f"Failed: {url}")

    logger.info("User ID column addition process completed")
    return len(failed) == 0


def _add_column_to_database(database_url):
    """Add the user_id column to the auth table using SQLAlchemy (db-agnostic)."""
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        dialect = engine.dialect.name

        with engine.connect() as connection:
            # Check if the auth table exists
            if not inspector.has_table("auth"):
                logger.warning(f"auth table does not exist in: {database_url}")
                return False

            # Check if column already exists
            columns = inspector.get_columns("auth")
            column_names = [col["name"] for col in columns]

            if "user_id" not in column_names:
                if dialect == "postgresql":
                    # PostgreSQL supports ADD COLUMN IF NOT EXISTS (v9.6+)
                    alter_statement = text(
                        "ALTER TABLE auth ADD COLUMN IF NOT EXISTS user_id VARCHAR(255)"
                    )
                elif dialect == "sqlite":
                    # SQLite does not support IF NOT EXISTS on ALTER TABLE
                    alter_statement = text(
                        "ALTER TABLE auth ADD COLUMN user_id VARCHAR(255)"
                    )
                else:
                    raise ValueError(f"Unsupported database dialect: {dialect}")

                connection.execute(alter_statement)
                connection.commit()
                logger.info(f"Successfully added user_id column ({dialect}): {database_url}")
            else:
                logger.info(f"Column user_id already exists, skipping: {database_url}")

            return True

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error on {database_url}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error on {database_url}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    add_user_id_column()