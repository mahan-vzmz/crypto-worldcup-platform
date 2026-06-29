"""Dashboard router rendering Jinja2 templates for the web interface."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.dependencies import get_crypto_service
from app.services.crypto_service import CryptoService
from app.utils.result import Ok

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="src/app/templates")


def _compact_number(value: object) -> str:
    """Format a large number compactly (e.g. 1.28T, 35.0B, 4.5M)."""
    try:
        n = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    for suffix, threshold in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= threshold:
            return f"{n / threshold:.2f}{suffix}"
    return f"{n:,.0f}"


templates.env.filters["compact"] = _compact_number


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(
    request: Request,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
) -> HTMLResponse:
    """Render the full dashboard with all panels."""
    crypto_res = await crypto_service.get_prices()

    crypto_prices = crypto_res.value if isinstance(crypto_res, Ok) else []

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "crypto_prices": crypto_prices,
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


@router.get("/coin/{symbol}", response_class=HTMLResponse)
async def coin_detail(
    request: Request,
    symbol: str,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
) -> HTMLResponse:
    """Render a detail page for a single asset: stats, chart, and history."""
    symbol_u = symbol.upper()

    crypto_res = await crypto_service.get_prices()
    prices = crypto_res.value if isinstance(crypto_res, Ok) else []
    price = next((p for p in prices if p.symbol.upper() == symbol_u), None)

    history_res = await crypto_service.get_price_history(symbol_u, limit=20)
    history = history_res.value if isinstance(history_res, Ok) else []

    return templates.TemplateResponse(
        request=request,
        name="coin_detail.html",
        context={"price": price, "symbol": symbol_u, "history": history},
    )
