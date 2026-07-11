from sqlalchemy.ext.asyncio import AsyncSession

class BaseRepository:
    """Base repository class providing access to the async database session."""
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
