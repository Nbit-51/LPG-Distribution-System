from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from app.auth import service

router = APIRouter(prefix="/auth", tags=["Auth"])

class AdminRegister(BaseModel):
    username: str; password: str; full_name: str
    email: str; role: str = "viewer"; agency_id: Optional[int] = None

class ConsumerRegister(BaseModel):
    full_name: str; email: Optional[str] = None; phone: str; address: str
    password: str; consumer_type: str = "domestic"; agency_id: int

class ConsumerLogin(BaseModel):
    phone: str; password: str

@router.post("/login")
def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    admin = service.authenticate_admin(form.username, form.password)
    token = service.create_access_token({"sub": str(admin["admin_id"])})
    return {"access_token": token, "token_type": "bearer",
            "role": admin["role"], "admin_id": admin["admin_id"], "full_name": admin["full_name"]}

@router.post("/register")
def admin_register(body: AdminRegister, current=Depends(service.require_superadmin)):
    try:
        admin = service.register_admin(body.username, body.password, body.full_name,
                                       body.email, body.role, body.agency_id)
        admin.pop("password_hash", None)
        return admin
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/me")
def admin_me(current=Depends(service.get_current_admin)):
    current.pop("password_hash", None)
    return current

@router.post("/consumer/register")
def consumer_register(body: ConsumerRegister):
    try:
        consumer = service.register_consumer_account(
            body.full_name, body.phone, body.address,
            body.password, body.consumer_type, body.agency_id, body.email)
        token = service.create_consumer_token(consumer["consumer_id"])
        return {"access_token": token, "token_type": "bearer",
                "consumer_id": consumer["consumer_id"], "full_name": consumer["full_name"],
                "phone": consumer["phone"], "consumer_type": consumer["consumer_type"],
                "agency_id": consumer["agency_id"], "address": consumer["address"]}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/consumer/login")
def consumer_login(body: ConsumerLogin):
    # Note: body.phone can be phone number or email address
    consumer = service.authenticate_consumer(body.phone, body.password)
    token = service.create_consumer_token(consumer["consumer_id"])
    return {"access_token": token, "token_type": "bearer",
            "consumer_id": consumer["consumer_id"], "full_name": consumer["full_name"],
            "phone": consumer["phone"], "consumer_type": consumer["consumer_type"],
            "agency_id": consumer["agency_id"], "address": consumer["address"]}

@router.get("/consumer/me")
def consumer_me(current=Depends(service.get_current_consumer)):
    current.pop("email", None)
    return current

class AgentLoginBody(BaseModel):
    phone: str
    password: str

@router.post("/agent/login")
def agent_login(body: AgentLoginBody):
    from app.delivery_agents import service as agent_svc
    agent = agent_svc.authenticate_agent(body.phone, body.password)
    token = service.create_agent_token(agent["agent_id"])
    return {"access_token": token, "token_type": "bearer",
            "agent_id": agent["agent_id"], "full_name": agent["full_name"],
            "phone": agent["phone"], "agency_id": agent["agency_id"]}

@router.get("/agent/me")
def agent_me(current=Depends(service.get_current_agent)):
    current.pop("password_hash", None)
    return current

class AgentRegisterBody(BaseModel):
    full_name: str
    phone: str
    agency_id: int
    password: str

@router.post("/agent/register")
def agent_register(body: AgentRegisterBody):
    from app.delivery_agents import service as agent_svc
    try:
        agent = agent_svc.create_delivery_agent(body.full_name, body.phone, body.agency_id, body.password)
        token = service.create_agent_token(agent["agent_id"])
        return {"access_token": token, "token_type": "bearer",
                "agent_id": agent["agent_id"], "full_name": agent["full_name"],
                "phone": agent["phone"], "agency_id": agent["agency_id"]}
    except ValueError as e:
        raise HTTPException(400, str(e))
