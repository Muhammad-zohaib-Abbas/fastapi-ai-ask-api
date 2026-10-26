"""Apply the database migrations required by PDF RAG."""

from pathlib import Path

from app.database import get_connection


MIGRATION_DIR = Path(__file__).resolve().parents[1] / "migrations"


def migrate() -> None:
    migration_files = sorted(MIGRATION_DIR.glob("*.sql"))
    if not migration_files:
        print("No database migrations found.")
        return

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for migration_file in migration_files:
                print(f"Applying {migration_file.name}...")
                cursor.execute(migration_file.read_text(encoding="utf-8"))

    print("Database migrations completed successfully.")


if __name__ == "__main__":
    migrate()
