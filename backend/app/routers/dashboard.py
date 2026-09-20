from fastapi import APIRouter, Depends

from ..deps import Container, get_container
from ..models.schemas import DashboardStats, HeatmapPoint

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(c: Container = Depends(get_container)):
    return DashboardStats(
        state_id=c.settings.state_id,
        state_name=c.settings.state_name,
        **c.store.query_stats(),
    )


@router.get("/heatmap", response_model=list[HeatmapPoint])
def heatmap(c: Container = Depends(get_container)):
    return c.store.heatmap_points()
