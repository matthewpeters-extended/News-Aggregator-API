from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.aggregator import run_aggregation
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AggregationRunOut

router = APIRouter(prefix="/aggregate", tags=["aggregation"])


@router.post("", response_model=AggregationRunOut)
def trigger_aggregation(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """Runs on a schedule (see app/scheduler.py) but any authenticated user
    can also trigger it on demand — useful for demos and for the mock-mode
    walkthrough in the README."""
    results = run_aggregation(db)
    return AggregationRunOut(mode=settings.app_mode, results=results)
