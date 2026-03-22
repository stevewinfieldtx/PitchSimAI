from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Persona
from schemas import PersonaCreate, PersonaResponse as PersonaSchema

router = APIRouter()


@router.get("", response_model=List[PersonaSchema])
async def list_personas(
    industry: Optional[str] = Query(None),
    company_size: Optional[str] = Query(None),
    buying_style: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Persona)
    if industry:
        query = query.where(Persona.industry == industry)
    if company_size:
        query = query.where(Persona.company_size == company_size)
    if buying_style:
        query = query.where(Persona.buying_style == buying_style)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=PersonaSchema, status_code=201)
async def create_persona(
    persona_data: PersonaCreate,
    db: AsyncSession = Depends(get_db),
):
    persona = Persona(**persona_data.model_dump())
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return persona


@router.get("/{persona_id}", response_model=PersonaSchema)
async def get_persona(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.put("/{persona_id}", response_model=PersonaSchema)
async def update_persona(
    persona_id: UUID,
    persona_data: PersonaCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    for key, value in persona_data.model_dump().items():
        setattr(persona, key, value)

    await db.commit()
    await db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    await db.delete(persona)
    await db.commit()


@router.get("/industries/list")
async def list_industries(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import distinct
    result = await db.execute(select(distinct(Persona.industry)))
    return [row[0] for row in result.all()]
