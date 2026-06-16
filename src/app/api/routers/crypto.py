from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_crypto_service
from app.models.crypto import Coin, CryptoPrice
from app.services.crypto_service import CryptoService
from app.utils.result import Err, Ok

router = APIRouter(prefix="/crypto", tags=["Crypto"])


@router.get("/prices", response_model=list[CryptoPrice])
def get_all_prices(
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
) -> list[CryptoPrice]:
    """Retrieve current prices for all supported cryptocurrencies."""
    result = crypto_service.get_prices(list(Coin))
    match result:
        case Ok(prices):
            return prices
        case Err(e):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from None
    assert_never(result)


@router.get("/prices/{symbol}", response_model=CryptoPrice)
def get_coin_price(
    symbol: str,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
) -> CryptoPrice:
    """Retrieve the current price for a specific cryptocurrency."""
    try:
        coin = Coin[symbol.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coin '{symbol}' is not supported.",
        ) from None

    result = crypto_service.get_prices([coin])
    match result:
        case Ok(prices):
            if not prices:
                raise HTTPException(status_code=404, detail="Price not found") from None
            return prices[0]
        case Err(e):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from None
    assert_never(result)


@router.get("/history/{symbol}", response_model=list[CryptoPrice])
def get_price_history(
    symbol: str,
    crypto_service: Annotated[CryptoService, Depends(get_crypto_service)],
    limit: int = 10,
) -> list[CryptoPrice]:
    """Retrieve the price history for a specific cryptocurrency."""
    try:
        coin = Coin[symbol.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coin '{symbol}' is not supported.",
        ) from None

    result = crypto_service.get_price_history(coin, limit=limit)
    match result:
        case Ok(prices):
            return prices
        case Err(e):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from None
    assert_never(result)
