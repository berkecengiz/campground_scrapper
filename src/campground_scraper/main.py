from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from campground_scraper.api.routes import scraper
from campground_scraper.db.session import create_tables
from campground_scraper.logging_config import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize and cleanup tasks for the application.
    """
    # Startup: Create database tables if they don't exist
    logger.info("Creating database tables if they don't exist")
    await create_tables()
    
    yield
    
    # Shutdown: Cleanup tasks
    logger.info("Shutting down application")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "campground-scraper"}

# Add this section to start the server when running the file directly
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")