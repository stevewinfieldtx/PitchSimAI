from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Persona
from services.buying_committee import generate_buying_committee, generate_persona_from_context
from services.linkedin_enrichment import enrich_from_linkedin_text, enrich_from_name_and_company

router = APIRouter()


# ---- Schemas ----

class CommitteeRequest(BaseModel):
    industry: str
    company_size: str = Field(description="small, mid-market, or enterprise")
    warmth: str = Field(default="mixed", description="friendly, mixed, or hostile")
    company_name: Optional[str] = None
    product_context: Optional[str] = Field(
        default=None,
        description="Brief description of what you're selling"
    )

class DynamicPersonaRequest(BaseModel):
    title: str
    industry: str
    company_size: str
    company_name: Optional[str] = None
    warmth: str = "mixed"

class LinkedInTextRequest(BaseModel):
    profile_text: str = Field(description="Copy-pasted text from a LinkedIn profile page")
    warmth: str = "mixed"

class NameCompanyRequest(BaseModel):
    name: str
    company: str
    title: Optional[str] = None
    warmth: str = "mixed"


# ---- Endpoints ----

@router.post("/generate")
async def generate_committee(
    request: CommitteeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        committee = await generate_buying_committee(
            industry=request.industry,
            company_size=request.company_size,
            warmth=request.warmth,
            company_name=request.company_name,
            product_context=request.product_context,
            save_to_db=True,
        )
        return {
            "committee_size": len(committee),
            "industry": request.industry,
            "company_size": request.company_size,
            "warmth": request.warmth,
            "members": committee,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Committee generation failed: {str(e)}")


@router.post("/generate-persona")
async def generate_single_persona(request: DynamicPersonaRequest):
    persona = await generate_persona_from_context(
        title=request.title,
        industry=request.industry,
        company_size=request.company_size,
        company_name=request.company_name,
        warmth=request.warmth,
    )
    return persona


@router.post("/enrich/linkedin")
async def enrich_from_linkedin(request: LinkedInTextRequest):
    result = await enrich_from_linkedin_text(
        profile_text=request.profile_text,
        warmth=request.warmth,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/enrich/name")
async def enrich_from_name(request: NameCompanyRequest):
    result = await enrich_from_name_and_company(
        name=request.name,
        company=request.company,
        title=request.title,
        warmth=request.warmth,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/warmth-options")
async def get_warmth_options():
    from services.buying_committee import WARMTH_PROFILES
    return {
        key: {"label": key.title(), "description": val["description"]}
        for key, val in WARMTH_PROFILES.items()
    }


@router.get("/industries")
async def get_supported_industries():
    from services.buying_committee import INDUSTRY_CONTEXT
    return {
        industry: {
            "departments": ctx["departments"],
            "key_concerns": ctx["key_concerns"],
        }
        for industry, ctx in INDUSTRY_CONTEXT.items()
    }
