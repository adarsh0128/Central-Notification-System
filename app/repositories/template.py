import uuid
from sqlalchemy import select
from app.models.template import Template
from app.repositories.base import BaseRepository
from app.schemas.template import TemplateCreate

class TemplateRepository(BaseRepository):
    async def get_by_id(self, template_id: uuid.UUID) -> Template | None:
        """Fetches a template by UUID."""
        stmt = select(Template).where(Template.id == template_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Template | None:
        """Fetches a template by its unique name."""
        stmt = select(Template).where(Template.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, template_in: TemplateCreate) -> Template:
        """Creates a new notification template in the database."""
        new_template = Template(
            name=template_in.name,
            subject=template_in.subject,
            content=template_in.content,
        )
        self.db.add(new_template)
        await self.db.commit()
        await self.db.refresh(new_template)
        return new_template

    async def list_all(self) -> list[Template]:
        """Lists all templates."""
        stmt = select(Template).order_by(Template.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
