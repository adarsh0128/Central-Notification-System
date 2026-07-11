from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.core.database import get_db
from app.repositories import TemplateRepository
from app.schemas import TemplateCreate, TemplateResponse

router = APIRouter()

@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=201,
    summary="Create a new template",
)
async def create_template(
    template_in: TemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = TemplateRepository(db)
    existing = await repo.get_by_name(template_in.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template with name '{template_in.name}' already exists."
        )
    result = await repo.create(template_in)
    return result

@router.get(
    "/templates",
    response_model=list[TemplateResponse],
    summary="List all templates",
)
async def list_templates(
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = TemplateRepository(db)
    result = await repo.list_all()
    return result
