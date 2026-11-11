
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Inventory
from app.schemas.inventory import InventoryResponse

router = APIRouter(prefix="/api/v1", tags=["inventory"])


@router.get(
    "/inventory/{sku}",
    response_model=InventoryResponse,
)
def get_inventory(sku: str, db: Session = Depends(get_db)):
    inventory = db.get(Inventory, sku)

    if inventory is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "SKU_NOT_FOUND",
                    "message": "Product SKU not found",
                }
            },
        )

    return InventoryResponse(
        sku=inventory.sku,
        available=inventory.available,
    )
