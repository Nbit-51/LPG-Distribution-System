import io, hashlib, json, base64
from datetime import datetime, timedelta, timezone
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from app.database import execute_query
from app.config import settings


def _build_token(booking_id: int, consumer_id: int) -> str:
    raw = f"{booking_id}:{consumer_id}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _render_qr(payload: dict) -> bytes:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    try:
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
    except Exception:
        img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr(booking_id: int) -> dict:
    # Check booking exists
    bookings = execute_query(
        """SELECT b.booking_id, b.consumer_id, b.agency_id,
                  b.cylinders_requested, b.status, b.booking_date,
                  c.full_name, c.phone, c.consumer_type,
                  a.agency_name
           FROM bookings b
           JOIN consumers c ON c.consumer_id = b.consumer_id
           JOIN agencies  a ON a.agency_id  = b.agency_id
           WHERE b.booking_id = %s""",
        (booking_id,)
    )
    if not bookings:
        raise ValueError(f"Booking {booking_id} not found.")

    booking = bookings[0]

    # Check if QR already exists
    existing = execute_query(
        "SELECT id, token FROM qr_codes WHERE booking_id = %s", (booking_id,)
    )
    if existing:
        token = existing[0]["token"]
        png   = _render_qr(json.loads(execute_query(
            "SELECT qr_payload FROM qr_codes WHERE booking_id = %s", (booking_id,)
        )[0]["qr_payload"]) if False else {"booking_id": booking_id, "token": token})
        return {
            "booking_id":  booking_id,
            "token":       token,
            "already_existed": True,
            "consumer_name": booking["full_name"],
            "png_bytes":   png,
            "png_b64":     base64.b64encode(png).decode(),
        }

    token   = _build_token(booking_id, booking["consumer_id"])
    expires = datetime.utcnow() + timedelta(days=settings.qr_validity_days)
    payload = {
        "booking_id":  booking_id,
        "consumer_id": booking["consumer_id"],
        "token":       token,
        "issued_at":   datetime.utcnow().isoformat(),
    }

    png    = _render_qr(payload)
    png_b64 = base64.b64encode(png).decode()

    execute_query(
        """INSERT INTO qr_codes (booking_id, token, qr_payload, qr_image_b64, expires_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (booking_id, token, json.dumps(payload), png_b64, expires),
        fetch=False,
    )
    execute_query(
        """UPDATE bookings
           SET qr_token=%s, qr_generated_at=NOW(), qr_expires_at=%s
           WHERE booking_id=%s""",
        (token, expires, booking_id),
        fetch=False,
    )

    return {
        "booking_id":    booking_id,
        "token":         token,
        "consumer_name": booking["full_name"],
        "consumer_type": booking["consumer_type"],
        "agency_name":   booking["agency_name"],
        "cylinders":     booking["cylinders_requested"],
        "expires_at":    expires.isoformat(),
        "png_b64":       png_b64,
        "png_bytes":     png,
    }


def get_qr(booking_id: int) -> dict | None:
    rows = execute_query(
        """SELECT q.id, q.booking_id, q.token, q.qr_payload,
                  q.qr_image_b64, q.expires_at, q.is_active, q.created_at,
                  b.cylinders_requested, b.booking_date, b.delivery_status,
                  c.full_name, c.phone, c.consumer_type,
                  a.agency_name
           FROM qr_codes q
           JOIN bookings  b ON b.booking_id  = q.booking_id
           JOIN consumers c ON c.consumer_id = b.consumer_id
           JOIN agencies  a ON a.agency_id   = b.agency_id
           WHERE q.booking_id = %s""",
        (booking_id,)
    )
    return rows[0] if rows else None


def process_scan(token: str, action: str, agent_id, device_info: str, ip: str) -> dict:
    rows = execute_query(
        """SELECT q.id, q.booking_id, q.token, q.expires_at, q.is_active,
                  b.consumer_id, b.cylinders_requested, b.delivery_status, b.status AS booking_status,
                  c.full_name, c.consumer_type,
                  a.agency_name
           FROM qr_codes q
           JOIN bookings  b ON b.booking_id  = q.booking_id
           JOIN consumers c ON c.consumer_id = b.consumer_id
           JOIN agencies  a ON a.agency_id   = b.agency_id
           WHERE q.token = %s""",
        (token,)
    )

    if not rows:
        return {"scan_result": "invalid", "valid": False}

    rec = rows[0]

    if not rec["is_active"]:
        _log_scan(rec["id"], agent_id, action, "invalid", device_info, ip)
        return {"scan_result": "invalid", "valid": False}

    expires = rec["expires_at"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires.replace(tzinfo=None) < datetime.utcnow():
        _log_scan(rec["id"], agent_id, action, "expired", device_info, ip)
        return {"scan_result": "expired", "valid": False}

    if action == "mark_delivered":
        execute_query(
            "UPDATE bookings SET delivery_status='delivered', delivered_at=NOW(), is_qr_used=1 WHERE booking_id=%s",
            (rec["booking_id"],), fetch=False
        )
        execute_query(
            "UPDATE qr_codes SET is_active=0 WHERE id=%s",
            (rec["id"],), fetch=False
        )

    _log_scan(rec["id"], agent_id, action, "valid", device_info, ip)

    return {
        "scan_result":   "valid",
        "valid":         True,
        "booking_id":    rec["booking_id"],
        "consumer_name": rec["full_name"],
        "consumer_type": rec["consumer_type"],
        "agency_name":   rec["agency_name"],
        "cylinders":     rec["cylinders_requested"],
        "delivery_status": rec["delivery_status"],
        "booking_status": rec["booking_status"],
    }



def _log_scan(qr_code_id, agent_id, action, result, device_info, ip):
    try:
        execute_query(
            """INSERT INTO qr_scan_logs (qr_code_id, agent_id, action, scan_result, device_info, ip_address)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (qr_code_id, agent_id, action, result, device_info, ip),
            fetch=False,
        )
    except Exception:
        pass
