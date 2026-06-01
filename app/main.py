import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

STATIC_DIR = os.path.join(os.getcwd(), "static")

from app.auth.routes       import router as auth_router
from app.consumers.routes  import router as consumers_router
from app.agencies.routes   import router as agencies_router
from app.bookings.routes   import router as bookings_router
from app.supply.routes     import router as supply_router
from app.allocation.routes import router as allocation_router
from app.admin.routes      import router as admin_router
from app.support.routes    import router as support_router
from app.delivery_agents.routes import router as delivery_agents_router
from app.invoices.routes import router as invoices_router

try:
    from app.qr.routes import router as qr_router
    HAS_QR = True
except ImportError as e:
    print(f"QR import failed: {e}")
    HAS_QR = False

app = FastAPI(title="LPG Distribution System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


app.include_router(auth_router)
app.include_router(consumers_router)
app.include_router(agencies_router)
app.include_router(bookings_router)
app.include_router(supply_router)
app.include_router(allocation_router)
app.include_router(admin_router)
app.include_router(support_router)
app.include_router(delivery_agents_router)
app.include_router(invoices_router)
if HAS_QR:
    app.include_router(qr_router)


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "landing.html"))

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "register.html"))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.get("/consumer-portal", response_class=HTMLResponse)
async def consumer_portal(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "consumer.html"))

@app.get("/consumers-page", response_class=HTMLResponse)
async def consumers_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "consumer.html"))

@app.get("/agencies-page", response_class=HTMLResponse)
async def agencies_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "agencies.html"))

@app.get("/bookings-page", response_class=HTMLResponse)
async def bookings_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "bookings.html"))

@app.get("/supply-page", response_class=HTMLResponse)
async def supply_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "supply.html"))

@app.get("/allocation-page", response_class=HTMLResponse)
async def allocation_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "allocation.html"))

@app.get("/allocation-lab", response_class=HTMLResponse)
async def allocation_lab(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "allocation_lab.html"))

@app.get("/qr-page", response_class=HTMLResponse)
async def qr_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "qr.html"))

@app.get("/reports-page", response_class=HTMLResponse)
async def reports_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "reports.html"))

@app.get("/policies-page", response_class=HTMLResponse)
async def policies_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "policies.html"))

@app.get("/invoices-page", response_class=HTMLResponse)
async def invoices_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "invoices.html"))





@app.get('/consumers-page-admin', response_class=HTMLResponse)
async def consumers_page_admin(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, 'consumers.html'))

@app.get("/delivery-portal", response_class=HTMLResponse)
async def delivery_portal(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "delivery.html"))

@app.get("/agents-page", response_class=HTMLResponse)
async def agents_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "agents.html"))

@app.get("/simulator-page", response_class=HTMLResponse)
async def simulator_page(request: Request):
    return FileResponse(os.path.join(STATIC_DIR, "simulator.html"))
