from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
 
from app.models.gov_scheme import GovScheme
from app.schemas.gov_scheme import (
    GovSchemeCreate,
    GovSchemeResponse,
    GovSchemeUpdate,
    SchemeEligibilityRequest,
    SchemeEligibilityResponse,
)
from app.services.gov_scheme_mutator import GovSchemeMutator, get_gov_scheme_mutator
from app.services.geo import normalize_admin

router = APIRouter(prefix="/gov-schemes", tags=["gov-schemes"])


def _to_response(gov_scheme: GovScheme) -> GovSchemeResponse:
    return GovSchemeResponse(
        id=str(gov_scheme.id),
        source_record_id=gov_scheme.source_record_id,
        name=gov_scheme.name,
        description=gov_scheme.description,
        eligibility_criteria=gov_scheme.eligibility_criteria,
        benefits=gov_scheme.benefits,
        required_documents=gov_scheme.required_documents,
        application_deadline=gov_scheme.application_deadline,
        application_steps=gov_scheme.application_steps,
        official_source_url=gov_scheme.official_source_url,
        applicable_states=gov_scheme.applicable_states,
        source=gov_scheme.source,
        fetched_at=gov_scheme.fetched_at,
    )


def _to_object_id(gov_scheme_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(gov_scheme_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid government scheme ID")


@router.post("", response_model=GovSchemeResponse, status_code=status.HTTP_201_CREATED)
async def create_gov_scheme(payload: GovSchemeCreate):
    gov_scheme = GovScheme(**payload.model_dump())
    await gov_scheme.insert()
    return _to_response(gov_scheme)


@router.get("", response_model=List[GovSchemeResponse])
async def list_gov_schemes():
    gov_schemes = await GovScheme.find_all().to_list()
    return [_to_response(gov_scheme) for gov_scheme in gov_schemes]


@router.get("/by-state/{state}", response_model=List[GovSchemeResponse])
async def list_gov_schemes_by_state(state: str):
    normalized_state = normalize_admin(state) or state.strip()
    # Beanie's list-field expression API differs across supported versions;
    # keep this small reference catalogue query deterministic and bounded.
    all_schemes = await GovScheme.find_all().to_list()
    gov_schemes = [
        scheme for scheme in all_schemes
        if not scheme.applicable_states
        or any(normalize_admin(value) == normalized_state for value in scheme.applicable_states)
        or any((normalize_admin(value) or "").casefold().startswith("india") for value in scheme.applicable_states)
    ]
    return [_to_response(gov_scheme) for gov_scheme in gov_schemes]


@router.post("/check-eligibility", response_model=SchemeEligibilityResponse)
async def check_scheme_eligibility(
    payload: SchemeEligibilityRequest,
    mutator: GovSchemeMutator = Depends(get_gov_scheme_mutator),
):
    gov_schemes = await mutator.check_scheme_eligibility(
        farmer_state=payload.farmer_state,
        eligibility_criteria=payload.eligibility_criteria,
    )
    return SchemeEligibilityResponse(
        farmer_state=payload.farmer_state,
        eligible_schemes=[_to_response(gov_scheme) for gov_scheme in gov_schemes],
    )


@router.get("/{gov_scheme_id}", response_model=GovSchemeResponse)
async def get_gov_scheme(gov_scheme_id: str):
    gov_scheme = await GovScheme.get(_to_object_id(gov_scheme_id))
    if not gov_scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Government scheme not found")
    return _to_response(gov_scheme)


@router.put("/{gov_scheme_id}", response_model=GovSchemeResponse)
async def update_gov_scheme(gov_scheme_id: str, payload: GovSchemeUpdate):
    gov_scheme = await GovScheme.get(_to_object_id(gov_scheme_id))
    if not gov_scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Government scheme not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(gov_scheme, field_name, value)
    await gov_scheme.save()
    return _to_response(gov_scheme)


@router.delete("/{gov_scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gov_scheme(gov_scheme_id: str):
    gov_scheme = await GovScheme.get(_to_object_id(gov_scheme_id))
    if not gov_scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Government scheme not found")
    await gov_scheme.delete()
