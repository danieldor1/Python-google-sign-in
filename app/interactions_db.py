#################################################
# -*- coding: utf-8 -*-
#################################################
# DB INTERACTION
#################################################

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.database import GoogleUser, GoogleSession
from app.schemas import HttpResponseFromDb
from app.config import DataBase

DATABASE_URL = DataBase.database_server_url.value

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def create_user_google(
    payload_data: dict
):
    db = SessionLocal()

    try:

        user_instance_from_db = db.query(GoogleUser).filter_by(
            email=payload_data['email']).first()

        if user_instance_from_db:
            
            return {
                "status_code": HttpResponseFromDb.DB_ACCESS_POINT_ALREADY_REGISTERED_CONFLICT.value,
                "user_id": user_instance_from_db.user_identifier
            }
        
        else:
            db_user = GoogleUser(
                id=payload_data['id'],
                email=payload_data['email'],
                family_name=payload_data.get('family_name'),
                given_name=payload_data.get('given_name'),
                locale=payload_data.get('locale'),
                name=payload_data.get('name'),
                picture=payload_data.get('picture'),
                verified_email=payload_data['verified_email']
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            user_id = db_user.user_identifier

        return {
            "status_code": HttpResponseFromDb.DB_ACCESS_POINT_REGISTER_SUCCESS.value,
            "user_id": user_id
        }

    except Exception as e:
        db.rollback()
        return {"status_code": HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value}

    finally:
        db.close()

async def create_session_google(
    user_id: str,
    token:str
) -> str:
    
    db = SessionLocal()
    
    try:
        db_user = GoogleSession(
            User_ID=user_id,
            Generated_Token=token,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return {
            "status_code": HttpResponseFromDb.DB_ACCESS_POINT_REGISTER_SUCCESS.value,
        }
    
    except IntegrityError:
        db.rollback()
        return {"status_code": HttpResponseFromDb.DB_ACCESS_POINT_ALREADY_REGISTERED_CONFLICT.value}

    except Exception:
        db.rollback()
        return {"status_code": HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value}

    finally:
        db.close()