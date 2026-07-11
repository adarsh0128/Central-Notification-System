from sqlalchemy import select
from app.models.user_preference import UserPreference
from app.repositories.base import BaseRepository
from app.schemas.preference import UserPreferenceRequest

class UserPreferenceRepository(BaseRepository):
    async def get_by_user_id(self, user_id: str) -> UserPreference | None:
        """Fetches preferences for a given user_id. Returns None if not found."""
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, pref: UserPreferenceRequest) -> UserPreference:
        """Upserts preference options for a user."""
        existing = await self.get_by_user_id(user_id)
        if existing:
            existing.email_enabled = pref.email_enabled
            existing.sms_enabled = pref.sms_enabled
            existing.push_enabled = pref.push_enabled
            self.db.add(existing)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            new_pref = UserPreference(
                user_id=user_id,
                email_enabled=pref.email_enabled,
                sms_enabled=pref.sms_enabled,
                push_enabled=pref.push_enabled,
            )
            self.db.add(new_pref)
            await self.db.commit()
            await self.db.refresh(new_pref)
            return new_pref
