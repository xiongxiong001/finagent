from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str
    version: str
    services: dict[str, str]
