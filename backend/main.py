import hashlib
import datetime
import pytz
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, root_validator
from jose import jwt, JWTError
from dotenv import load_dotenv

from database import Base, engine, SessionLocal, enable_pg_trgm
from models import User, Log
from auth import router as auth_router
from config import SECRET_KEY, ALGORITHM

import query_pipeline
import frontend  # python module, not nextjs

# Load env vars
load_dotenv()

# App initialization
app = FastAPI()

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # IMPORTANT
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes
app.include_router(auth_router)

security = HTTPBearer()

# Token verification
def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# DB init
def create_default_user():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            user = User(
                username="admin",
                password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

# Schemas
class ChatRequest(BaseModel):
    query: str

class EventData(BaseModel):
    name_of_event: str
    event_domain: str
    date_of_event: str
    description_insights: str
    time_of_event: Optional[str] = ""
    faculty_coordinators: Optional[str] = ""
    student_coordinators: Optional[str] = ""
    venue: Optional[str] = ""
    mode_of_event: Optional[str] = "Offline"
    registration_fee: Optional[str] = "0"
    speakers: Optional[str] = ""
    perks: Optional[str] = ""
    collaboration: Optional[str] = ""

    @root_validator(pre=True)
    def empty_str_to_nan(cls, values):
        for key, value in values.items():
            if value == "":
                values[key] = "0" if key == "registration_fee" else "NaN"
        return values

# Routes
@app.get("/")
def health_check():
    return {"status": "Club Knowledge Agent is active"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    db = SessionLocal()
    try:
        response_data = query_pipeline.handle_user_query(request.query)
        response_text = response_data["answer"]
        sql_query = response_data["sql_query"]

        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.datetime.now(ist)

        new_log = Log(
            date=now.strftime("%d-%m-%Y"),
            time=now.strftime("%H:%M:%S"),
            question=request.query,
            answer=response_text,
            sql_query=sql_query,
        )
        db.add(new_log)
        db.commit()

        return {"answer": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/add-event")
def add_event_endpoint(
    event: EventData,
    _: dict = Depends(verify_token),
):
    return frontend.add_new_event(event.dict())

@app.get("/api/verify-token")
def verify_token_endpoint(_: dict = Depends(verify_token)):
    return {"status": "success", "message": "Token is valid"}

# Startup
enable_pg_trgm()
Base.metadata.create_all(bind=engine)
create_default_user()
