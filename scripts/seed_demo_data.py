"""One-off: create a demo user and run aggregation so there's data to browse
immediately after `uvicorn app.main:app` starts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.aggregator import run_aggregation
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

existing = db.query(User).filter(User.email == "demo@news-aggregator.dev").first()
if existing:
    print("Demo user already exists.")
else:
    demo_user = User(
        name="Demo User",
        email="demo@news-aggregator.dev",
        password=hash_password("demo12345"),
    )
    db.add(demo_user)
    db.commit()
    print("Created demo@news-aggregator.dev / demo12345")

results = run_aggregation(db)
for result in results:
    print(f"{result.provider}: fetched {result.fetched}, created {result.created}, skipped {result.skipped_duplicates}")

db.close()
