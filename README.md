# Campground Scraper

A web scraping solution for extracting and managing campground data from TheDyrt.com across the United States.

## Overview

This project scrapes, stores, and manages campground data from TheDyrt.com, covering all campground locations across the continental United States. It utilizes TheDyrt's public search API to efficiently extract detailed campground information while respecting API rate limits.

The backend is built with FastAPI and leverages async scraping for performance. Data is stored in a PostgreSQL database, with the system containerized using Docker for consistent deployment. The project also includes a REST API layer for querying and accessing stored campground data.
## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/campground-scraper.git
   cd campground-scraper
   ```

2. Configure environment variables by creating a `.env` file:
   ```
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=campgrounds
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   
   # Scraper settings
   CONCURRENCY_LIMIT=3
   GRID_SIZE=1.0
   ```

3. Build and start the containers:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

### Required Dependencies

Add these to your requirements.txt:

```
fastapi>=0.68.0
uvicorn>=0.15.0
sqlalchemy>=1.4.0
asyncpg>=0.25.0
pydantic>=1.9.0
httpx>=0.21.0
tenacity>=8.0.0
tqdm>=4.62.0
python-dotenv>=0.19.0
fastapi-utils==0.2.1
typing-inspect>=0.7.1
typing-extensions>=4.0.0
mypy-extensions>=0.4.3
```

## Project Structure

```
campground_scraper/
├── api/                   # API endpoints
│   └── routes/
│       └── scraper.py     # Scraper API routes
├── db/                    # Database components
│   ├── session.py         # Session management
│   └── operations.py      # Database operations
├── models/                # Data models
│   ├── campground.py      # Pydantic model
│   └── campground_db.py   # SQLAlchemy model
├── scraper/               # Scraper components
│   ├── scraper.py         # Main scraper logic
│   └── client.py          # TheDyrt API client
├── settings.py            # Configuration settings
├── logging.py      # Logging configuration
└── main.py                # Application entry point
```

## API Endpoints

The following endpoints are available:

- `GET /`: Health check endpoint
- `GET /api/scraper/status`: Get current scraper status
- `POST /api/scraper/run`: Trigger a scraper job manually

### Example API Requests

```bash
# Check scraper status
curl http://localhost:8000/api/scraper/status

# Start a scraper job
curl -X POST http://localhost:8000/api/scraper/run
```

## Database Schema

The scraper uses two main tables:

### Campgrounds Table

Stores the scraped campground data:

- `id` (TEXT, PK): Unique identifier
- `name` (TEXT): Campground name
- `latitude` (FLOAT): Latitude coordinate
- `longitude` (FLOAT): Longitude coordinate
- `region_name` (TEXT): State or region
- `administrative_area` (TEXT): Administrative area (e.g., National Park)
- `nearest_city_name` (TEXT): Nearest city
- `operator` (TEXT): Campground operator
- `photo_url` (TEXT): Primary photo URL
- `rating` (FLOAT): Average rating
- `reviews_count` (INT): Number of reviews
- `price_low` (FLOAT): Minimum price
- `price_high` (FLOAT): Maximum price
- `address` (TEXT): Full address (if available)
- `created_at` (TIMESTAMP): Record creation timestamp
- `updated_at` (TIMESTAMP): Record update timestamp

### Scraper Stats Table

Tracks statistics for each scraper run:

- `id` (INT, PK): Run identifier
- `run_date` (TIMESTAMP): Timestamp of the run
- `total_campgrounds` (INT): Total campgrounds found
- `new_campgrounds` (INT): New campgrounds added
- `updated_campgrounds` (INT): Existing campgrounds updated
- `regions_count` (INT): Number of regions covered
- `min_latitude`, `max_latitude`, `min_longitude`, `max_longitude` (FLOAT): Geographical bounds
- `duration_seconds` (FLOAT): Run duration in seconds
- `error_message` (TEXT): Error message if any

## Configuration

The scraper can be configured through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database username | postgres |
| `POSTGRES_PASSWORD` | Database password | postgres |
| `POSTGRES_HOST` | Database host | postgres |
| `POSTGRES_PORT` | Database port | 5432 |
| `POSTGRES_DB` | Database name | campgrounds |
| `CONCURRENCY_LIMIT` | Maximum concurrent requests | 3 |
| `GRID_SIZE` | Grid cell size in degrees | 1.0 |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | INFO |

## Scheduling

The scraper is configured to run automatically once per day. This scheduled job ensures data is regularly refreshed without manual intervention.

## Troubleshooting

### Common Issues

1. **Database Connection Errors**: 
   - Ensure PostgreSQL is running and connection parameters are correct
   - Check that database tables have been created

2. **Missing Dependencies**:
   - If you encounter missing module errors, check your requirements.txt and install:
     ```
     pip install fastapi-utils typing-inspect
     ```

3. **API Not Accessible**:
   - Verify the container is running: `docker-compose ps`
   - Check the container logs: `docker-compose logs -f api`
   - Ensure you're using the correct URL with the prefix: `/api/scraper/*`

4. **Container Restarts**:
   - If containers are repeatedly restarting, check logs for errors
   - Ensure environment variables are properly set

## Implementation Details

### Scraper Logic

The scraper divides the US map into grid cells and processes each cell to find campgrounds. It uses controlled concurrency to avoid overwhelming the API and implements retry logic for robustness.

### Database Integration

SQLAlchemy models provide an ORM layer for interacting with the PostgreSQL database. Async support enables non-blocking database operations, improving overall performance.

### API Endpoints

FastAPI provides REST endpoints for controlling and monitoring the scraper. Background tasks are used to run the scraper without blocking API responses.

### Scheduling

A cron-like scheduler ensures regular data updates without manual intervention. The scheduler is implemented using the `repeat_every` decorator from fastapi-utils.
