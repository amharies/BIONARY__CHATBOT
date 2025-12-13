# backend/database.py
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Use Neon if available, otherwise fall back to local sqlite (for dev)
DATABASE_URL = os.getenv("NEON_DB_URL")
if not DATABASE_URL:
    raise RuntimeError("NEON_DB_URL is not set. Please configure it in your .env file.")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🔴 THIS is what was missing / broken
Base = declarative_base()


def enable_pg_trgm():
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        connection.commit()

