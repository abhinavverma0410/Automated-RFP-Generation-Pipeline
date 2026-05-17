from sqlalchemy import create_engine
# create_engine() is the starting point of any SQLAlchemy application
# It creates a connection pool to your PostgreSQL database
# Think of it as opening a persistent phone line to the database
# It takes your DATABASE_URL and figures out which database driver to use

from sqlalchemy.orm import sessionmaker, DeclarativeBase
# sessionmaker — a factory (blueprint) for creating database sessions
# Every time your code wants to talk to the DB, it creates a session from this factory
# Think of a session as a single conversation with the database —
# you make changes, then either commit (save) or rollback (undo)

# DeclarativeBase — the base class all your table models inherit from
# In SQLAlchemy 2.x, you inherit from DeclarativeBase as a class
# SQLAlchemy uses it to track which Python classes map to which DB tables
# Without it, SQLAlchemy wouldn't know your Tender class is a database table

from dotenv import load_dotenv
import os

# Load environment variables from .env file into os.environ
load_dotenv()

# Read the database connection URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the SQLAlchemy engine — this is the actual connection to PostgreSQL
# The engine manages the low-level database connection pool
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory that creates new database sessions
# autoflush=False — don't automatically sync changes to DB before every query
# expire_on_commit=False — keep objects accessible after a commit without re-querying
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Base class for all database models
# Any class that inherits from Base will be treated as a database table by SQLAlchemy
class Base(DeclarativeBase):
    pass

# Dependency function that provides a database session to whoever calls it
# Used by FastAPI route functions to get a DB session per request

def get_database():
    database = SessionLocal()  # Open a new session
    try:
        yield database         # Hand the session to the caller
    finally:
        database.close()       # Always close the session when done, even if an error occurs