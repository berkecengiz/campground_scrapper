from fastapi import FastAPI
from campground_scraper.api.routes import scraper
from campground_scraper.db.session import create_tables

app = FastAPI(
    title="Campground Scraper API",
    description="API to control and monitor campground scraping jobs.",
    version="1.0.0"
)

app.include_router(scraper.router, prefix="/scraper", tags=["Scraper"])

@app.get("/")
async def root():
    return {"message": "Campground Scraper API is running."}
