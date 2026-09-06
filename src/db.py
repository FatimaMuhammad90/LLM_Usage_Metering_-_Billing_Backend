# db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# convo with the databae is done through this sessionmkaer
sessionLocal = sessionmaker    (bind=engine, autoflush=False,autocommit=False)


class Base(DeclarativeBase):
    pass