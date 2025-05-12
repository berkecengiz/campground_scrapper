import asyncio
from typing import List, Set, Tuple, Dict, Any, Optional
from tqdm.asyncio import tqdm
import tenacity
import json
from datetime import datetime

from campground_scraper.models.campground import Campground
from campground_scraper.logging_config import get_logger
from campground_scraper.scraper.client import TheDyrtClient

logger = get_logger(__name__)

class Scraper:
    """
    Main scraper for TheDyrt campground data across the United States
    Uses a grid-based approach to ensure complete coverage
    """

    # US continental boundaries plus Alaska and Hawaii
    US_BOUNDARIES = {
        "CONTINENTAL": {
            "NORTH": 49.5,   # Northern border with Canada
            "SOUTH": 24.5,   # Southern tip of Florida
            "EAST": -66.0,   # Eastern Maine
            "WEST": -125.0,  # Western coast
        },
        "ALASKA": {
            "NORTH": 71.5,
            "SOUTH": 51.0,
            "EAST": -130.0,
            "WEST": -170.0,
        },
        "HAWAII": {
            "NORTH": 22.5,
            "SOUTH": 18.5,
            "EAST": -154.5,
            "WEST": -160.5,
        }
    }

    def __init__(
        self,
        concurrency_limit: int = 3,
        pages_per_cell: int = 2,        # Get first 2 pages per cell for better coverage
        grid_size: float = 1.0,         # 1 degree grid cells (smaller than default)
        save_interval: int = 100        # Save to DB every 100 campgrounds
    ):
        self.concurrency_limit = concurrency_limit
        self.pages_per_cell = pages_per_cell
        self.grid_size = grid_size
        self.save_interval = save_interval
        self.client = TheDyrtClient(semaphore_limit=concurrency_limit)
        self.total_campgrounds_found = 0
        self.start_time = datetime.now()

    def generate_us_grid_cells(self) -> List[Tuple[float, float, float, float]]:
        """
        Generate grid cells covering the entire United States.
        Includes Continental US, Alaska, and Hawaii.
        """
        grid_cells = []

        # Generate cells for each US region
        for region_name, boundaries in self.US_BOUNDARIES.items():
            cells = self._generate_cells_for_region(
                boundaries["NORTH"], 
                boundaries["SOUTH"], 
                boundaries["EAST"], 
                boundaries["WEST"],
                region_name
            )
            grid_cells.extend(cells)

        logger.info(f"Generated {len(grid_cells)} grid cells for US regions")
        return grid_cells

    def _generate_cells_for_region(
        self, north: float, south: float, east: float, west: float, region_name: str
    ) -> List[Tuple[float, float, float, float]]:
        """Generate grid cells for a specific region."""
        cells = []

        lat_steps = int((north - south) / self.grid_size) + 1
        for i in range(lat_steps):
            cell_south = south + i * self.grid_size
            cell_north = min(cell_south + self.grid_size, north)

            lon_steps = int((east - west) / self.grid_size) + 1
            for j in range(lon_steps):
                cell_west = west + j * self.grid_size
                cell_east = min(cell_west + self.grid_size, east)

                cells.append((cell_north, cell_south, cell_east, cell_west))

        logger.info(f"Generated {len(cells)} cells for {region_name}")
        return cells

    def validate_campground_data(self, camp_data: Dict[str, Any]) -> Optional[Campground]:
        """
        Validate campground data before creating a Campground instance.
        """
        if not camp_data:
            return None
            
        try:
            # Try to create the Campground instance with Pydantic validation
            campground = Campground(**camp_data)
            return campground
        except Exception as e:
            camp_id = camp_data.get("id", "unknown")
            logger.error(f"Error validating campground {camp_id}: {e}")
            return None

    async def process_grid_cell(self, cell: Tuple[float, float, float, float], seen_ids: Set[str]) -> List[Campground]:
        """
        Process a single grid cell with specified pages per cell.
        """
        north, south, east, west = cell
        campgrounds = []

        try:
            logger.debug(f"Fetching campgrounds for cell N:{north:.2f} S:{south:.2f} E:{east:.2f} W:{west:.2f}")
            
            # Fetch multiple pages per cell
            campgrounds_data = []
            for page in range(1, self.pages_per_cell + 1):
                page_data = await self.client.fetch_campgrounds_by_bounds(
                    north=north, south=south, east=east, west=west, page=page
                )
                
                if not page_data:
                    break
                    
                campgrounds_data.extend(page_data)
                
                # Small delay between pages
                await asyncio.sleep(0.2)

            new_campgrounds = []
            for camp_data in campgrounds_data:
                if not camp_data:
                    continue
                    
                camp_id = camp_data.get("id")
                if not camp_id or camp_id in seen_ids:
                    continue
                    
                # Validate and create campground
                campground = self.validate_campground_data(camp_data)
                if campground:
                    new_campgrounds.append(campground)
                    seen_ids.add(camp_id)
                    self.total_campgrounds_found += 1

            campgrounds.extend(new_campgrounds)
            if new_campgrounds:
                logger.info(f"Cell N:{north:.2f} S:{south:.2f} E:{east:.2f} W:{west:.2f} - Found {len(new_campgrounds)} new campgrounds")

            return campgrounds

        except tenacity.RetryError as e:
            logger.error(f"RetryError processing grid cell N:{north:.2f} S:{south:.2f} E:{east:.2f} W:{west:.2f}: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Error processing grid cell N:{north:.2f} S:{south:.2f} E:{east:.2f} W:{west:.2f}: {e}")
            return []

    async def scan_map(self, save_callback=None) -> List[Campground]:
        """
        Scan the entire US map, with option to save incrementally.
        
        Args:
            save_callback: Optional function to save campgrounds incrementally
                           Should accept a list of Campground objects
        """
        all_campgrounds = []
        seen_ids = set()
        self.total_campgrounds_found = 0
        self.start_time = datetime.now()

        grid_cells = self.generate_us_grid_cells()
        logger.info(f"Starting to process {len(grid_cells)} grid cells across the US")
        
        # Process cells with controlled concurrency
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        
        async def process_with_semaphore(cell):
            async with semaphore:
                return await self.process_grid_cell(cell, seen_ids)
        
        # Process cells in batches to control memory usage
        batch_size = 20
        campgrounds_since_last_save = []
        
        for i in range(0, len(grid_cells), batch_size):
            batch = grid_cells[i:i+batch_size]
            
            tasks = [process_with_semaphore(cell) for cell in batch]
            batch_results = await tqdm.gather(*tasks, 
                desc=f"Batch {i//batch_size + 1}/{(len(grid_cells) + batch_size - 1) // batch_size}")
            
            # Collect new campgrounds
            batch_campgrounds = []
            for campground_list in batch_results:
                if campground_list:
                    batch_campgrounds.extend(campground_list)
            
            all_campgrounds.extend(batch_campgrounds)
            campgrounds_since_last_save.extend(batch_campgrounds)
            
            # Log progress
            elapsed = (datetime.now() - self.start_time).total_seconds() / 60
            logger.info(f"Completed batch {i//batch_size + 1}/{(len(grid_cells) + batch_size - 1) // batch_size}. "
                       f"Total campgrounds: {self.total_campgrounds_found} "
                       f"(~{self.total_campgrounds_found / elapsed:.1f} campgrounds/minute)")
            
            # Save incrementally if callback provided
            if save_callback and len(campgrounds_since_last_save) >= self.save_interval:
                try:
                    await save_callback(campgrounds_since_last_save)
                    logger.info(f"Saved batch of {len(campgrounds_since_last_save)} campgrounds to database")
                    campgrounds_since_last_save = []
                except Exception as e:
                    logger.error(f"Error during incremental save: {e}")
            
            # Small delay between batches
            await asyncio.sleep(1)

        # Final save of any remaining campgrounds
        if save_callback and campgrounds_since_last_save:
            try:
                await save_callback(campgrounds_since_last_save)
                logger.info(f"Saved final batch of {len(campgrounds_since_last_save)} campgrounds to database")
            except Exception as e:
                logger.error(f"Error during final incremental save: {e}")

        logger.info(f"Scan complete. Total campgrounds found: {self.total_campgrounds_found}")
        return all_campgrounds
        
    async def save_campgrounds(self, campgrounds: List[Campground], filename: str = "campgrounds.json"):
        """
        Save the campground data to a JSON file.
        """
        if not campgrounds:
            logger.warning("No campgrounds to save")
            return
            
        try:
            # Convert campgrounds to dictionaries
            campground_dicts = []
            for camp in campgrounds:
                try:
                    # Use model_dump() if available (Pydantic v2) or dict() (Pydantic v1)
                    if hasattr(camp, 'model_dump'):
                        camp_dict = camp.model_dump()
                    else:
                        camp_dict = camp.dict()
                    
                    # Handle datetime objects
                    if 'availability_updated_at' in camp_dict and camp_dict['availability_updated_at']:
                        camp_dict['availability_updated_at'] = camp_dict['availability_updated_at'].isoformat()
                        
                    campground_dicts.append(camp_dict)
                except Exception as e:
                    logger.error(f"Error converting campground to dict: {e}")
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(campground_dicts, f, indent=2)
                
            logger.info(f"Successfully saved {len(campgrounds)} campgrounds to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving campgrounds to file: {e}")
            
    async def run(self, db_ops=None, output_file: str = None):
        """
        Run the scraper with database support.
        
        Args:
            db_ops: Database operations object for saving to database
            output_file: Optional file path to save JSON data
        """
        logger.info("Starting TheDyrt campground scraper for all US locations")
        
        # Define incremental save callback if db_ops provided
        save_callback = None
        if db_ops:
            async def save_to_db(campgrounds):
                result = await db_ops.save_campgrounds_bulk_async(campgrounds)
                return result
            save_callback = save_to_db
        
        # Scan the map with incremental saving
        campgrounds = await self.scan_map(save_callback=save_callback)
        
        # Save final results to file if requested
        if output_file:
            await self.save_campgrounds(campgrounds, output_file)
        
        # Return statistics
        return {
            "total_campgrounds": self.total_campgrounds_found,
            "elapsed_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
            "regions_covered": len(self.US_BOUNDARIES)
        }