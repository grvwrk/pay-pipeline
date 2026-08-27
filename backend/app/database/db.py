import os
import json
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings
from backend.app.database.models import Base, ProductModel

CATALOG_JSON_PATH = Path(settings.CATALOG_DB_PATH)
if not CATALOG_JSON_PATH.is_absolute():
    CATALOG_JSON_PATH = (Path(__file__).resolve().parent.parent.parent / settings.CATALOG_DB_PATH).resolve()

connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(db: Session = None):
    """Create all database tables and seed catalog data if not already populated."""
    Base.metadata.create_all(bind=engine)

    def _seed(session: Session):
        existing_count = session.query(ProductModel).count()
        if existing_count == 0 and CATALOG_JSON_PATH.exists():
            try:
                with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
                    products_data = json.load(f)
                    for item in products_data:
                        product = ProductModel(
                            id=item["id"],
                            name=item["name"],
                            category=item["category"],
                            price=float(item["price"]),
                            inventory=int(item.get("inventory", 0)),
                            rating=float(item.get("rating", 4.5)),
                            specs_json=json.dumps(item.get("specs", {})),
                            tags_json=json.dumps(item.get("tags", [])),
                            complementary_ids_json=json.dumps(item.get("complementary_product_ids", [])),
                            description=item.get("description", "")
                        )
                        session.add(product)
                    session.commit()
            except Exception as e:
                session.rollback()
                print(f"[Database] Warning: Failed to seed catalog: {e}")

    if db:
        _seed(db)
    else:
        with SessionLocal() as session:
            _seed(session)