import os

from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    DateTime,
    func,
    Boolean
)

from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# DB GOOGLE TABLE_NAME
GOOGLE_SESSIONS_TABLE_NAME = os.getenv('GOOGLE_SESSIONS_TABLE_NAME')
GOOGLE_REGISTRATION_TABLE_NAME = os.getenv("GOOGLE_REGISTRATION_TABLE_NAME")

# DB INSTANCE
Base = declarative_base()

class GoogleSession(Base):

    __tablename__ = GOOGLE_SESSIONS_TABLE_NAME

    Session_Key = Column(Integer, primary_key=True, autoincrement=True)
    User_ID = Column(String(255), unique=False, nullable=False)
    Generated_Token = Column(String(500), unique=True, nullable=False)


class GoogleUser(Base):

    __tablename__ = GOOGLE_REGISTRATION_TABLE_NAME

    user_identifier = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    family_name = Column(String(255))
    given_name = Column(String(255))
    id = Column(BigInteger)
    locale = Column(String(10))
    name = Column(String(255))
    picture = Column(String(255))
    verified_email = Column(Boolean)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=func.current_timestamp())
    last_login = Column(DateTime)


