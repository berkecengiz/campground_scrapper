import asyncio
import time
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi_utils.tasks import repeat_every
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from campground_scraper.scraper.scraper import Scraper
from campground_scraper.db.session import get_async_session, get_session, close_session
from campground_scraper.db.operations import DBOperations
from src.campground_scraper.logging import get_logger
from campground_scraper.settings import CONCURRENCY_LIMIT, GRID_SIZE, BATCH_SIZE

router = APIRouter()
logger = get_logger(__name__)

# Status tracking
scraper_status = {
    "running": False,
    "last_run": None,
    "last_run_stats": None,
    "error": None
}

@router.get("/status")
async def get_scraper_status():
    """Get the current status of the scraper."""
    return scraper_status

@router.post("/run", status_code=202)
async def run_scraper(background_tasks: BackgroundTasks):
    """Trigger the scraper job asynchronously."""
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Scraper is already running")
        
    logger.info("Scraper job accepted.")
    background_tasks.add_task(_scraper_task)
    
    scraper_status["running"] = True
    scraper_status["error"] = None
    
    return {"status": "Scraper started in background."}

@router.on_event("startup")
@repeat_every(seconds=60 * 60 * 24, wait_first=True)  # Run every 24 hours
async def scheduled_scraper():
    """Run the scraper at scheduled intervals if not already running."""
    if not scraper_status["running"]:
        logger.info("Starting scheduled scraper job")
        await _scraper_task()
    else:
        logger.info("Scheduled job skipped - scraper already running")

async def _scraper_task():
    """Asynchronous task to run the scraper and save results to database."""
    scraper_status["running"] = True
    scraper_status["error"] = None
    
    start_time = time.time()
    total_campgrounds = 0
    new_campgrounds = 0
    updated_campgrounds = 0
    error_message = None
    regions_count = 0
    
    session = None
    
    try:
        logger.info("Starting US campground scraper job")
        
        session = await get_session()
        db_ops = DBOperations(session)
        
        scraper = Scraper(
            concurrency_limit=CONCURRENCY_LIMIT,
            pages_per_cell=2,
            grid_size=GRID_SIZE
        )
        
        stats = await scraper.run(db_ops=db_ops)
        
        total_campgrounds = stats["total_campgrounds"]
        regions_count = stats.get("regions_covered", 0)
        
        min_lat = scraper.US_BOUNDARIES["SOUTH"]  
        max_lat = scraper.US_BOUNDARIES["NORTH"]
        min_lon = scraper.US_BOUNDARIES["WEST"]
        max_lon = scraper.US_BOUNDARIES["EAST"]

        if hasattr(db_ops, "last_operation_stats"):
            new_campgrounds = db_ops.last_operation_stats.get("new", 0)
            updated_campgrounds = db_ops.last_operation_stats.get("updated", 0)
        
    except Exception as e:
        logger.error(f"Error in scraper job: {e}")
        error_message = str(e)
        scraper_status["error"] = str(e)
    finally:
        duration = time.time() - start_time
        
        try:
            if session:
                await db_ops.save_stats(
                    total=total_campgrounds,
                    new=new_campgrounds,
                    updated=updated_campgrounds,
                    duration=duration,
                    regions_count=regions_count,
                    min_latitude=min_lat,
                    max_latitude=max_lat,
                    min_longitude=min_lon,
                    max_longitude=max_lon,
                    error_message=error_message
                )
                
                await close_session(session)
        except Exception as e:
            logger.error(f"Error saving scraper stats: {e}")
            if session:
                await close_session(session)
                
        scraper_status["running"] = False
        scraper_status["last_run"] = datetime.now().isoformat()
        scraper_status["last_run_stats"] = {
            "total": total_campgrounds,
            "new": new_campgrounds,
            "updated": updated_campgrounds,
            "duration": duration,
            "error": error_message
        }