"""Dashboard router rendering Jinja2 templates for the web interface."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.dependencies import get_crypto_service, get_football_service
from app.services.crypto_service import CryptoService
from app.services.football_service import FootballService
from app.utils.result import Ok

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(
    request: Request,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
    football_service: Annotated[FootballService, Depends(get_football_service)],
) -> HTMLResponse:
    """Render the full dashboard with all panels."""
    crypto_res = await crypto_service.get_prices()
    football_res = await football_service.get_tournament("WC")

    crypto_prices = crypto_res.value if isinstance(crypto_res, Ok) else []
    tournament = football_res.value if isinstance(football_res, Ok) else None

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "crypto_prices": crypto_prices,
            "tournament": tournament,
        },
    )


@router.get("/partials/crypto", response_class=HTMLResponse)
async def partial_crypto(
    request: Request,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
) -> HTMLResponse:
    """Render the crypto table partial for HTMX polling."""
    crypto_res = await crypto_service.get_prices()
    crypto_prices = crypto_res.value if isinstance(crypto_res, Ok) else []

    return templates.TemplateResponse(
        request=request,
        name="partials/crypto_table.html",
        context={"crypto_prices": crypto_prices},
    )


@router.get("/partials/football/{competition_code}", response_class=HTMLResponse)
async def partial_football(
    request: Request,
    competition_code: str,
    football_service: Annotated[FootballService, Depends(get_football_service)],
) -> HTMLResponse:
    """Render the football table partial for HTMX polling."""
    football_res = await football_service.get_tournament(competition_code)
    tournament = football_res.value if isinstance(football_res, Ok) else None

    return templates.TemplateResponse(
        request=request,
        name="partials/football_table.html",
        context={"tournament": tournament},
    )
