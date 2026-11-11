
from app.database import SessionLocal
from app.models import Inventory, Product

PRODUCTS = [
    {
        "sku": "KIT-100",
        "unit_price_cents": 1299,
        "initial_stock": 7,
    },
    {
        "sku": "PART-200",
        "unit_price_cents": 599,
        "initial_stock": 12,
    },
    {
        "sku": "PACK-300",
        "unit_price_cents": 249,
        "initial_stock": 5,
    },
]


def seed_catalog():
    db = SessionLocal()

    try:
        for item in PRODUCTS:
            sku = item["sku"]

            # Insert the product only if it does not already exist.
            product = db.get(Product, sku)

            if product is None:
                db.add(
                    Product(
                        sku=sku,
                        unit_price_cents=item["unit_price_cents"],
                    )
                )
                db.flush()

            # Insert initial inventory only if it does not exist.
            inventory = db.get(Inventory, sku)

            if inventory is None:
                db.add(
                    Inventory(
                        sku=sku,
                        available=item["initial_stock"],
                    )
                )

        db.commit()
        print("Catalog and inventory seed completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_catalog()
