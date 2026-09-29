from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorReadingCreate(BaseModel):
    sensor_id: str
    moisture_percent: float
    temperature_c: float

class SensorReadingUpdate(BaseModel):
    moisture_percent: Optional[float] = None
    temperature_c: Optional[float] = None