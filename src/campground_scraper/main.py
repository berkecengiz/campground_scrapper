import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from campground_scraper.api.routes import scraper
from campground_scraper.db.session import create_tables
from campground_scraper.logging import get_logger
from campground_scraper.scraper.scraper import Scraper
from campground_scraper.db.operations import DBOperations
from campground_scraper.db.session import create_tables, get_session, close_session

logger = get_logger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Campground Scraper API",
        description="API to control and monitor campground scraping jobs.",
        version="1.0.0"
    )
    
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
        
    return app

async def run_scraper():
    """Run the scraper directly."""
    logger.info("Starting scraper")
    await create_tables()
    
    session = await get_session()
    db_ops = DBOperations(session)
    
    try:
        scraper = Scraper()
        stats = await scraper.run(db_ops=db_ops)
        logger.info(f"Scraper completed: {stats}")
    finally:
        await close_session(session)

if __name__ == "__main__":
    import uvicorn
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "scrape":
            asyncio.run(run_scraper())
        elif command == "api":
            app = create_app()
            logger.info("Starting API server...")
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        else:
            logger.error(f"Unknown command: {command}")
            sys.exit(1)
    else:
        app = create_app()
        logger.info("Starting API server (default)...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")