from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from backend.schemas import CheckoutRequest, CheckoutResponse
from backend.services.stripe import build_mock_checkout_url, build_success_redirect_url

router = APIRouter()


@router.post("/api/payments/create-checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest) -> CheckoutResponse:
    # Simply point mock Stripe success stub
    return CheckoutResponse(checkout_url=build_mock_checkout_url(request.vin))


@router.get("/api/payments/success-stub")
async def success_stub(request: Request, session_id: str, vin: str) -> RedirectResponse:
    # Forward all query params (including extras like promo, referrer) to the frontend
    extra = {
        k: v for k, v in request.query_params.items() if k not in ("session_id", "vin")
    }
    redirect_url = build_success_redirect_url(session_id, vin, extra)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/payments/webhook")
async def webhook() -> dict[str, str]:
    return {"status": "received"}
