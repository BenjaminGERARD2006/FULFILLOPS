
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.catalog import CatalogResponse

router = APIRouter(prefix="/api/v1", tags=["catalog"])


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog(db: Session = Depends(get_db)):
    products = db.scalars(
        select(Product).order_by(Product.sku)
    ).all()

    return CatalogResponse(products=products)
