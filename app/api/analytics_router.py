from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_user_scope_center
from app.services.analytics_service import get_dashboard_analytics, get_employee_dashboard_analytics
from app.services.cache_service import cache
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics & BI"])


@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve workforce KPIs for Admins/Managers or self-service dashboard metrics for Employees (with intelligent caching)."""
    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        cache_key = f"analytics:emp:{current_user.employee_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        data = get_employee_dashboard_analytics(db, employee_id=current_user.employee_id)
        cache.set(cache_key, data, ttl_seconds=120)
        return data

    scoped_center = get_user_scope_center(db, current_user)
    center_key = scoped_center or "all"
    cache_key = f"analytics:admin:{center_key}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = get_dashboard_analytics(db, center=scoped_center)
    cache.set(cache_key, data, ttl_seconds=300)
    return data
