
from pydantic import BaseModel


class InventoryResponse(BaseModel):
    sku: str
    available: int
