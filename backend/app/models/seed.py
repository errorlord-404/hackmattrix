from beanie import Document


class Seed(Document):
    crop: str
    variety: str
    duration_days: str
    yield_potential: str
    disease_resistance: str
    recommended_zone: str

    class Settings:
        name = "seeds"
