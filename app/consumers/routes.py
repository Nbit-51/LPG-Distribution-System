from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List

# Importing from the schemas we just fixed
from app.consumers.schemas import (
    ConsumerCreate, ConsumerUpdate,
    ConsumerResponse, ConsumerListResponse, MessageResponse,
    ConsumerType, KYCSubmit, WalletAddFunds, WalletVerifyPayment,
    AutoRefillToggle
)
from app.consumers import service
from app.auth.service import get_current_consumer

# This 'router' variable is what main.py is looking for!
router = APIRouter(prefix="/consumers", tags=["Consumers"])

@router.post("/", response_model=ConsumerResponse, status_code=201)
def register_consumer(body: ConsumerCreate):
    try:
        record = service.create_consumer(body)
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/", response_model=ConsumerListResponse)
def list_consumers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    consumer_type: Optional[ConsumerType] = Query(None),
    agency_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    try:
        return service.list_consumers(
            page=page,
            page_size=page_size,
            consumer_type=consumer_type,
            agency_id=agency_id,
            is_active=is_active,
            search=search,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.post("/kyc/submit", response_model=ConsumerResponse)
def submit_consumer_kyc(body: KYCSubmit, current_consumer=Depends(get_current_consumer)):
    try:
        record = service.submit_kyc(current_consumer["consumer_id"], body.doc_type, body.doc_num)
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/cylinder-status")
def get_cylinder_status(current_consumer=Depends(get_current_consumer)):
    try:
        status = service.get_cylinder_status(current_consumer["consumer_id"])
        if not status:
            raise HTTPException(status_code=404, detail="Consumer not found.")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.post("/auto-refill/toggle")
def toggle_auto_refill(body: AutoRefillToggle, current_consumer=Depends(get_current_consumer)):
    try:
        return service.toggle_auto_refill(
            current_consumer["consumer_id"],
            body.enabled,
            current_consumer["agency_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/{consumer_id}", response_model=ConsumerResponse)
def get_consumer(consumer_id: int):
    record = service.get_consumer_by_id(consumer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Consumer not found.")
    return record

@router.patch("/{consumer_id}", response_model=ConsumerResponse)
def update_consumer(consumer_id: int, body: ConsumerUpdate):
    try:
        return service.update_consumer(consumer_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.delete("/{consumer_id}", response_model=MessageResponse)
def deactivate_consumer(consumer_id: int):
    try:
        service.deactivate_consumer(consumer_id)
        return {"message": "Consumer deactivated.", "consumer_id": consumer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/me")
def get_my_wallet(current_consumer=Depends(get_current_consumer)):
    try:
        return service.get_wallet(current_consumer["consumer_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wallet/add-funds")
def add_wallet_funds_order(body: WalletAddFunds, current_consumer=Depends(get_current_consumer)):
    import random
    mock_order_id = f"order_demo_{random.randint(100000, 999999)}"
    return {
        "order_id": mock_order_id,
        "amount": body.amount,
        "currency": "INR",
        "key": "rzp_test_mockkey"
    }

@router.post("/wallet/verify-payment")
def verify_wallet_payment(body: WalletVerifyPayment, current_consumer=Depends(get_current_consumer)):
    try:
        updated_wallet = service.add_wallet_funds(
            current_consumer["consumer_id"],
            body.amount,
            f"Wallet Topup via Razorpay (Ref: {body.razorpay_payment_id})"
        )
        return {"status": "success", "wallet": updated_wallet}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))