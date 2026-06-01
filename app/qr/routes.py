import io
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.qr import service

router = APIRouter(prefix="/qr", tags=["QR Codes"])


class GenerateQR(BaseModel):
    booking_id: int


class ScanQR(BaseModel):
    token:       str
    action:      str = "view_details"
    agent_id:    Optional[int] = None
    device_info: Optional[str] = ""


SCAN_MESSAGES = {
    "valid":        "QR verified successfully.",
    "invalid":      "Invalid or deactivated QR code.",
    "expired":      "QR code has expired.",
    "already_used": "Already used — delivery previously confirmed.",
}


@router.post("/generate")
def generate(body: GenerateQR):
    try:
        result = service.generate_qr(body.booking_id)
        result.pop("png_bytes", None)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/{booking_id}")
def get_qr(booking_id: int):
    record = service.get_qr(booking_id)
    if not record:
        raise HTTPException(404, "QR not found for this booking.")
    return record


@router.get("/{booking_id}/download")
def download_qr(booking_id: int):
    record = service.get_qr(booking_id)
    if not record:
        raise HTTPException(404, "QR not found.")
    import json
    payload = json.loads(record["qr_payload"]) if isinstance(record["qr_payload"], str) else record["qr_payload"]
    png     = service._render_qr(payload)
    return StreamingResponse(
        io.BytesIO(png), media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="booking_{booking_id}_qr.png"'},
    )


@router.post("/scan")
def scan(body: ScanQR, request: Request):
    if body.action not in ("view_details", "verify_identity", "mark_delivered"):
        raise HTTPException(400, "Invalid action.")
    ip     = request.client.host if request.client else ""
    result = service.process_scan(body.token, body.action, body.agent_id, body.device_info or "", ip)
    return {**result, "message": SCAN_MESSAGES.get(result["scan_result"], "Unknown.")}