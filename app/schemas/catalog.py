
from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    unit_price_cents: int


class CatalogResponse(BaseModel):
    products: list[ProductResponse]
