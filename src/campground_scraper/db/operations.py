from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, text
from typing import List, Dict, Any, Optional
from datetime import datetime

from campground_scraper.models.campground import Campground
from campground_scraper.models.campground_db import CampgroundTable, ScraperStats 
from src.campground_scraper.logging import get_logger

logger = get_logger(__name__)

class DBOperations:
    """Database operations with async support for scraper data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_stats(
        self,
        total: int,
        new: int,
        updated: int,
        duration: float,
        regions_count: int = 0,
        min_latitude: float = 0,
        max_latitude: float = 0,
        min_longitude: float = 0,
        max_longitude: float = 0,
        error_message: str = None,
    ):
        """Save scraper statistics with async support."""
        try:
            stats = ScraperStats(
                total_campgrounds=total,
                new_campgrounds=new,
                updated_campgrounds=updated,
                regions_count=regions_count,
                min_latitude=min_latitude,
                max_latitude=max_latitude,
                min_longitude=min_longitude,
                max_longitude=max_longitude,
                duration_seconds=duration,
                error_message=error_message,
            )
            self.session.add(stats)
            await self.session.commit()
            logger.info(f"Scraper stats saved: {total} total, {new} new, {updated} updated")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save scraper stats: {e}")
            raise

    async def save_campgrounds_bulk_async(self, campgrounds: List[Campground]) -> Dict[str, int]:
        """
        Save campgrounds using efficient bulk operations with asyncio support.
        """
        if not campgrounds:
            logger.warning("No campgrounds to save")
            return {"new": 0, "updated": 0}
            
        try:
            campground_dicts = []
            for camp in campgrounds:
                camp_dict = self._convert_pydantic_to_db_dict(camp)
                if camp_dict:
                    campground_dicts.append(camp_dict)
            
            ids = [camp['id'] for camp in campground_dicts]
            
            stmt = select(CampgroundTable.id).where(CampgroundTable.id.in_(ids))
            result = await self.session.execute(stmt)
            existing_ids = set(row[0] for row in result)
            
            new_records = []
            update_records = []
            
            for camp_dict in campground_dicts:
                if camp_dict['id'] in existing_ids:
                    update_records.append(camp_dict)
                else:
                    new_records.append(camp_dict)
            
            if new_records:
                for record in new_records:
                    campground = CampgroundTable(**record)
                    self.session.add(campground)
            
            if update_records:
                for record in update_records:
                    stmt = select(CampgroundTable).where(CampgroundTable.id == record["id"])
                    result = await self.session.execute(stmt)
                    db_camp = result.scalar_one_or_none()
                    
                    if db_camp:
                        # Update fields
                        for key, value in record.items():
                            if key != 'id':  # Don't update primary key
                                setattr(db_camp, key, value)
                        
                        # Update timestamp
                        db_camp.updated_at = datetime.utcnow()
            
            # Commit all changes
            await self.session.commit()
            
            logger.info(f"Bulk async save: {len(new_records)} new, {len(update_records)} updated campgrounds")
            return {"new": len(new_records), "updated": len(update_records)}
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in bulk async save operation: {e}")
            raise
    
    def _convert_pydantic_to_db_dict(self, campground: Campground) -> Dict[str, Any]:
        """
        Convert a Pydantic Campground model to a dict for the SQLAlchemy model.
        """
        try:
            # Convert to dict
            if hasattr(campground, 'dict'):
                camp_dict = campground.dict(exclude_unset=True)
            else:
                camp_dict = campground.model_dump(exclude_unset=True)
            
            if 'region-name' in camp_dict:
                camp_dict['region_name'] = camp_dict.pop('region-name')
                
            fields_to_remove = [
                'links',
                'photo_urls',  
                'photos_count',
                'accommodation_type_names', 
            ]
            
            for field in fields_to_remove:
                camp_dict.pop(field, None)
                
            return camp_dict
            
        except Exception as e:
            logger.error(f"Error converting Pydantic model to dict: {e}")
            return {}