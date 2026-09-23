import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from database.db import Database


if __name__ == "__main__":
    database = Database(settings.database_path)
    database.initialize()
    print(f"Database ready: {database.path}")
