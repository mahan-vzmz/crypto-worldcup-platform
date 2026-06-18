from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_football_service
from app.models.football import Tournament
from app.services.football_service import FootballService
from app.utils.result import Err, Ok

router = APIRouter(prefix="/football", tags=["Football"])


@router.get("/tournament", response_model=Tournament)
async def get_tournament(
    football_service: Annotated[FootballService, Depends(get_football_service)],
) -> Tournament:
    """Retrieve the current state of the football tournament (World Cup)."""
    result = await football_service.get_tournament()
    match result:
        case Ok(tournament):
            return tournament
        case Err(e):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from None
    assert_never(result)
