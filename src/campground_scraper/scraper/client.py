import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.campground_scraper.logging import get_logger

logger = get_logger(__name__)

class TheDyrtClient:
    """API client for TheDyrt.com optimized for US coverage"""

    def __init__(self, semaphore_limit: int = 3):
        self.base_url = "https://thedyrt.com/api/v6"
        self.search_endpoint = f"{self.base_url}/locations/search-results"
        self.details_endpoint = f"{self.base_url}/locations"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://thedyrt.com/search",
        }

        self.semaphore = asyncio.Semaphore(semaphore_limit)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ReadTimeout, httpx.ConnectError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60)
    )
    async def fetch_campgrounds_by_bounds(
        self, 
        north: float, 
        south: float, 
        east: float, 
        west: float, 
        limit: int = 30,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch campgrounds within specified geographical bounds.
        """
        params = {
            "ne": f"{north},{east}",
            "sw": f"{south},{west}",
            "page[size]": limit,
            "page[number]": page
        }

        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_keepalive_connections=5)) as client:
                try:
                    response = await client.get(
                        self.search_endpoint, 
                        params=params, 
                        headers=self.headers
                    )
                    response.raise_for_status()

                    data = response.json()
                    
                    if not isinstance(data, dict):
                        logger.error(f"Unexpected response format (not dict): {data}")
                        return []

                    if "data" not in data:
                        logger.error(f"Unexpected response structure - missing 'data': {data}")
                        return []

                    campgrounds = data["data"]

                    if not isinstance(campgrounds, list):
                        logger.error(f"Expected 'data' to be a list, got: {type(campgrounds)}")
                        return []

                    # Process each campground to match model
                    processed_campgrounds = []
                    for camp in campgrounds:
                        processed_camp = self._process_campground(camp)
                        if processed_camp:
                            processed_campgrounds.append(processed_camp)
                    
                    return processed_campgrounds
                
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error {e.response.status_code} fetching campgrounds: {e}")
                    # If we get a 429 (Too Many Requests), wait longer
                    if e.response.status_code == 429:
                        await asyncio.sleep(10)  # Wait 10 seconds on rate limit
                    raise
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    return []
                    
                except Exception as e:
                    logger.error(f"Unexpected error fetching campgrounds: {e}")
                    raise
    
    def _process_campground(self, camp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a campground from the API response to match our Pydantic model structure.
        """
        if not isinstance(camp, dict):
            logger.error(f"Expected campground to be a dict, got: {type(camp)}")
            return {}
            
        try:
            campground_data = {
                "id": camp.get("id", ""),
                "type": camp.get("type", ""),
                "links": camp.get("links", {"self": ""})
            }

            attributes = camp.get("attributes", {})
            if not attributes:
                logger.warning(f"Campground {camp.get('id', 'unknown')} has no attributes")
                return {}
                
            campground_data.update(attributes)
            
            if "name" not in campground_data or not campground_data["name"]:
                logger.warning(f"Campground missing required 'name' field: {camp.get('id', 'unknown')}")
                return {}
            
            if "latitude" not in campground_data or "longitude" not in campground_data:
                logger.warning(f"Campground missing coordinates: {camp.get('id', 'unknown')}")
                return {}
                
            if "region-name" not in campground_data or not campground_data["region-name"]:
                logger.warning(f"Campground missing region-name: {camp.get('id', 'unknown')}")
                return {}
                
            if "photo-urls" in campground_data and not isinstance(campground_data["photo-urls"], list):
                campground_data["photo-urls"] = []
                
            if "camper-types" in campground_data and not isinstance(campground_data["camper-types"], list):
                campground_data["camper-types"] = []
                
            if "accommodation-type-names" in campground_data and not isinstance(campground_data["accommodation-type-names"], list):
                campground_data["accommodation-type-names"] = []
                
            return campground_data
            
        except Exception as e:
            logger.error(f"Error processing campground data: {e}")
            return {}

    def _process_campground_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Process the campground details response."""
        if not details or not isinstance(details, dict):
            return {}
            
        try:
            processed_details = {
                "id": details.get("id", ""),
                "type": details.get("type", ""),
                "links": details.get("links", {"self": ""})
            }
            
            if "attributes" in details and isinstance(details["attributes"], dict):
                processed_details.update(details["attributes"])
                
            return processed_details
            
        except Exception as e:
            logger.error(f"Error processing campground details: {e}")
            return {}