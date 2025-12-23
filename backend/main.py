import hashlib
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, root_validator
from jose import jwt, JWTError
from dotenv import load_dotenv
import datetime
import pytz

from database import Base, engine, SessionLocal
from models import User, Log
from auth import router as auth_router

# Load Environment Variables
load_dotenv()

# Your existing logic
import query_pipeline
import frontend  # python module, not nextjs

from config import SECRET_KEY, ALGORITHM

# App Initialization
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

# Token Verification Dependency
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

# Database Initialization
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

# Data Models
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
                if key == "registration_fee":
                    values[key] = "0"
                else:
                    values[key] = "NaN"
        return values

# Routes
@app.get("/")
def health_check():
    return {"status": "Club Knowledge Agent is active"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    db = SessionLocal() # Acquire a database session
    try:
        print("Incoming query:", request.query)
        response_data = query_pipeline.handle_user_query(request.query) # Store the response data
        response_text = response_data["answer"]
        sql_query = response_data["sql_query"]
        print("Agent response generated")

        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.datetime.now(ist)
        
        # Format date and time
        date_str = now_ist.strftime('%d-%m-%Y')
        time_str = now_ist.strftime('%H:%M:%S')

        # Create a new Log entry
        new_log = Log(
            date=date_str,
            time=time_str,
            question=request.query,
            answer=response_text,
            sql_query=sql_query
        )
        db.add(new_log)
        db.commit() # Commit the new log entry
        db.refresh(new_log) # Refresh to get the generated ID and timestamp

        return {"answer": response_text}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close() # Close the database session


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

@app.get("/api/verify-token")
def verify_token_endpoint(_: dict = Depends(verify_token)):
    return {"status": "success", "message": "Token is valid"}



# Startup
from database import enable_pg_trgm
enable_pg_trgm()
Base.metadata.create_all(bind=engine)
create_default_user()

# Run with:
# uvicorn main:app --reload
