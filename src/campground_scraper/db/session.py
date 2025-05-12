from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from campground_scraper.settings import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB

# Async SQLAlchemy engine
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory with async support
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Explicitly define an async context manager class
class AsyncSessionManager:
    """Async session context manager for database operations."""
    
    async def __aenter__(self):
        """Get a new session when entering context."""
        self.session = AsyncSessionLocal()
        return self.session
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the session when exiting context."""
        await self.session.close()

# Function to get the session manager
def get_async_session():
    """Get an async session context manager."""
    return AsyncSessionManager()

# Alternative: Simple function to get a session directly
async def get_session():
    """Get a database session (must be closed manually)."""
    return AsyncSessionLocal()

async def close_session(session):
    """Close a database session."""
    await session.close()

async def create_tables():
    """Create all database tables asynchronously."""
    from campground_scraper.models.campground_db import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)