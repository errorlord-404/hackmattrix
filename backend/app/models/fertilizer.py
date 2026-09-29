from typing import List

from beanie import Document
from pydantic import Field


class Fertilizer(Document):
    name: str
    type: str
    bag_size: str
    subsidized_mrp: float
    govt_subsidy_per_bag: float
    dosage_per_acre: str
    suitable_crops: List[str] = Field(default_factory=list)

    class Settings:
        name = "fertilizers"
