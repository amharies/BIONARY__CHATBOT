import hashlib
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from dotenv import load_dotenv

from database import Base, engine, SessionLocal
from models import User
from auth import router as auth_router

# ────────────────────────────────────────────────
# LOAD ENV
# ────────────────────────────────────────────────
load_dotenv()

# Your existing logic
import query_pipeline
import frontend  # python module, not nextjs

from config import SECRET_KEY, ALGORITHM

# ────────────────────────────────────────────────
# APP
# ────────────────────────────────────────────────
app = FastAPI()

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /auth/login
app.include_router(auth_router)

security = HTTPBearer()

# ────────────────────────────────────────────────
# TOKEN VERIFICATION DEPENDENCY
# ────────────────────────────────────────────────
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

# ────────────────────────────────────────────────
# DB INIT
# ────────────────────────────────────────────────
def create_default_user():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            user = User(
                username="admin",
                password_hash=hashlib.sha256(
                    "admin123".encode()
                ).hexdigest(),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

# ────────────────────────────────────────────────
# DATA MODELS
# ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str

class EventData(BaseModel):
    name_of_event: str
    event_domain: str
    date_of_event: str
    description_insights: str
    time_of_event: Optional[str] = "N/A"
    faculty_coordinators: Optional[str] = "N/A"
    student_coordinators: Optional[str] = "N/A"
    venue: Optional[str] = "N/A"
    mode_of_event: Optional[str] = "Offline"
    registration_fee: Optional[str] = "0"
    speakers: Optional[str] = "N/A"
    perks: Optional[str] = "N/A"
    collaboration: Optional[str] = "N/A"

# ────────────────────────────────────────────────
# ROUTES
# ────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "Club Knowledge Agent is active"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    try:
        print("➡️ Incoming query:", request.query)
        response = query_pipeline.handle_user_query(request.query)
        print("✅ Agent response generated")
        return {"answer": response}

    except Exception as e:
        import traceback
        traceback.print_exc()   # 🔥 THIS IS THE KEY PART
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/add-event")
def add_event_endpoint(
    event: EventData,
    _: dict = Depends(verify_token),
):
    try:
        result = frontend.add_new_event(event.dict())
        return result
    except Exception as e:
        print("ADD EVENT ERROR:", e)  # keep this
        raise HTTPException(status_code=500, detail=str(e))



# ────────────────────────────────────────────────
# STARTUP
# ────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
create_default_user()

# Run with:
# uvicorn main:app --reload
