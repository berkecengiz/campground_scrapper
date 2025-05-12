import os

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "campgrounds")

CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "3"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "30"))
GRID_SIZE = float(os.getenv("GRID_SIZE", "1.0"))

NORTH_BOUNDARY = float(os.getenv("NORTH_BOUNDARY", "49.5"))
SOUTH_BOUNDARY = float(os.getenv("SOUTH_BOUNDARY", "24.5"))
EAST_BOUNDARY = float(os.getenv("EAST_BOUNDARY", "-66.0"))
WEST_BOUNDARY = float(os.getenv("WEST_BOUNDARY", "-125.0"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")