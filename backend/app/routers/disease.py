from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from app.models.disease import Disease
from app.schemas.disease import DiseaseCreate, DiseaseResponse, DiseaseUpdate

router = APIRouter(prefix="/diseases", tags=["diseases"])


def _to_response(disease: Disease) -> DiseaseResponse:
    return DiseaseResponse(
        id=str(disease.id),
        crop_name=disease.crop_name,
        disease_name=disease.disease_name,
        symptoms=disease.symptoms,
        severity_levels=disease.severity_levels,
        treatment_recommendation=disease.treatment_recommendation,
    )


def _to_object_id(disease_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(disease_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid disease ID")


@router.post("", response_model=DiseaseResponse, status_code=status.HTTP_201_CREATED)
async def create_disease(payload: DiseaseCreate):
    disease = Disease(**payload.model_dump())
    await disease.insert()
    return _to_response(disease)


@router.get("", response_model=List[DiseaseResponse])
async def list_diseases():
    diseases = await Disease.find_all().to_list()
    return [_to_response(disease) for disease in diseases]


@router.get("/{disease_id}", response_model=DiseaseResponse)
async def get_disease(disease_id: str):
    disease = await Disease.get(_to_object_id(disease_id))
    if not disease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disease not found")
    return _to_response(disease)


@router.put("/{disease_id}", response_model=DiseaseResponse)
async def update_disease(disease_id: str, payload: DiseaseUpdate):
    disease = await Disease.get(_to_object_id(disease_id))
    if not disease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disease not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(disease, field_name, value)
    await disease.save()
    return _to_response(disease)


@router.delete("/{disease_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_disease(disease_id: str):
    disease = await Disease.get(_to_object_id(disease_id))
    if not disease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disease not found")
    await disease.delete()
