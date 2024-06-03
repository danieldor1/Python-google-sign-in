# -*- coding: utf-8 -*-
import os
import jwt
import requests
import traceback

from jwt.exceptions import InvalidTokenError
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status, FastAPI, Header
from fastapi.responses import RedirectResponse
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from google_auth_oauthlib.flow import Flow
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db import GoogleUser, GoogleSession
from app.schemas import HttpResponseFromDb
from app.token_creators import TokenCreatorForAuthFlow
from dotenv import load_dotenv

load_dotenv()

# GOOGLE API KEYS
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

#URL
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
URL = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# LOGINS
ENCRYPTION_ALGORITHM_SECRET_KEY = os.getenv("SECRET_KEY")
ENCRYPTION_ALGORITHM = os.getenv("ENCRYPTION_ALGORITHM")

#DB
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

client_secrets_file = Path(__file__).parent / "client_secret.json"

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=SCOPES,
    redirect_uri=GOOGLE_REDIRECT_URI
)

#################################################
# DB INTERACTION
#################################################

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
    
    except IntegrityError as e:
        print("IntegrityError occurred:", e)
        db.rollback()
        return {"status_code": HttpResponseFromDb.DB_ACCESS_POINT_ALREADY_REGISTERED_CONFLICT.value}

    except Exception as e:
        print("Unexpected error occurred:", e)
        db.rollback()
        return {"status_code": HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value}

    finally:
        db.close()

#################################################
# AUTH TOKEN
#################################################

async def verify_user(token:str) -> Optional[GoogleUser]:

    db = SessionLocal()

    try:
        # print(token)

        decoded_token = jwt.decode(
            token,
            key=ENCRYPTION_ALGORITHM_SECRET_KEY,
            algorithms=ENCRYPTION_ALGORITHM,
        )

        email = decoded_token.get('user_email')

        if email:
            user = db.query(GoogleUser).filter(
                GoogleUser.email == email).first()
            if not user:
                return f"user not found"

        return f"valid"

    except jwt.ExpiredSignatureError:
        return f"expired"

    except (
        InvalidTokenError,
        jwt.InvalidIssuerError,
        jwt.InvalidAudienceError
    ):
        return f"invalid"

@app.post("/verify-token")
async def verify_token(authorization: str = Header(...)):
    """
    Verify the validity of a token extracted from the authorization header
    """
    try:
        if authorization.startswith("Bearer "):
            token = str(authorization.split("Bearer ")[1])
            response = await verify_user(token=token)
            return {"detail": response}

        # Raise an exception for invalid authorization header
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header please include a Bearer token."
            )
    except HTTPException as e:
        # Catch any HTTP exceptions and return a response with the detail
        return {"detail": e.detail}


##################################################
# REGISTER: ENDPOINT FOR GOOGLE/ACCESS CALLBACK 
##################################################

@app.get('/login/google')
async def login_google():
    return {"url": URL}


@app.get('/oauth2callback')
async def oauth2callback(code: str,request: Request)->RedirectResponse:

    if code is None:
        raise HTTPException(
            status_code=400,
            detail="Code parameter not provided"
        )

    try:

        authorization_response = f"{request.base_url.scheme}://{request.base_url.netloc}{request.url}"
        
        flow.fetch_token(
            authorization_response=authorization_response
        )

        credentials = flow.credentials

        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )

        recieved_user_info_json = user_info_response.json()

        recieved_response_from_the_google_reg_db = await create_user_google(
            payload_data=recieved_user_info_json
        )

        recieved_user_info_json['user_id'] = recieved_response_from_the_google_reg_db['user_id']

        returned_token = TokenCreatorForAuthFlow.create_token(
            payload_to_encript=recieved_user_info_json
        )

        response_status_code_from_the_session_db = await create_session_google(
            user_id=recieved_response_from_the_google_reg_db.get('user_id'),
            token=returned_token
        )

        if recieved_response_from_the_google_reg_db["status_code"] == HttpResponseFromDb.DB_ACCESS_POINT_REGISTER_SUCCESS.value:
            deeplink_url = f'app_deeplink://status=created&token={returned_token}'

        if (recieved_response_from_the_google_reg_db.get("status_code") == HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value
                or response_status_code_from_the_session_db.get("status_code") == HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value):
            deeplink_url = f'app_deeplink://status=login_failed&token=**&error_code={HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value}'
        
        elif recieved_response_from_the_google_reg_db["status_code"] == HttpResponseFromDb.DB_ACCESS_POINT_ALREADY_REGISTERED_CONFLICT.value:
            deeplink_url = f'app_deeplink://status=authenticated&token={returned_token}'

        return RedirectResponse(
            url=deeplink_url
        )
        
    except Exception:
        trace = traceback.format_exc()
        deeplink_url = f'app_deeplink://status=login_failed&token=**&error_code={trace}'
        return RedirectResponse(
            url=deeplink_url
        )



##########################################
# TEST ZONE
###########################################
# 
# from fastapi.responses import HTMLResponse
# 
# 
# @app.get('/oauth2callback', response_class=HTMLResponse)
# async def oauth2callback(
#     code: str,
#     request: Request
# ):
# 
#     if code is None:
#         raise HTTPException(
#             status_code=400,
#             detail="Code parameter not provided"
#         )
# 
#     try:
#         print("*+")
# 
#         authorization_response = f"{request.base_url.scheme}://{request.base_url.netloc}{request.url}"
#         flow.fetch_token(
#             authorization_response=authorization_response
#         )
#         print("*++")
# 
#         credentials = flow.credentials
#         print("*+++")
# 
#         user_info_response = requests.get(
#             "https://www.googleapis.com/oauth2/v1/userinfo",
#             headers={"Authorization": f"Bearer {credentials.token}"}
#         )
# 
#         print("*")
# 
#         encoded_json_user_info = user_info_response.json()
# 
#         print(encoded_json_user_info)
# 
#         response_data_from_the_db = await create_user_google(payload_data=encoded_json_user_info
#                                                              )
# 
#         print(response_data_from_the_db, "*")
# 
#         # agrega el el campo user_id del campo status code from the db
#         encoded_json_user_info['user_id'] = response_data_from_the_db['user_id']
# 
#         returned_token = TokenCreatorForAuthFlow.create_token(
#             payload_to_encript=encoded_json_user_info
#         )
#         
#         print(response_data_from_the_db.get('user_id'))
# 
#         session_saver = await create_session_google(
#             user_id=response_data_from_the_db.get('user_id'),
#             token=returned_token)
# 
#         print(session_saver)
# 
#         if response_data_from_the_db["status_code"] == 200:
#             return RedirectResponse(url=f"/success?message=registered&token={returned_token}")
# 
#         elif response_data_from_the_db["status_code"] == 409:
#             return RedirectResponse(url=f"/success?message=already&token={returned_token}")
# 
#     except Exception as e:
#         print(e)
#         print("**")
#         return RedirectResponse(url="/error")
# 
# 
# @app.get("/success", response_class=HTMLResponse)
# async def success(message: str, token: str):
#     return f"<h1>{message}</h1><p>Token: {token}</p>"
# 
# 
# @app.get("/error", response_class=HTMLResponse)
# async def error():
#     return "<h1>An error occurred</h1>"




##########################################
# RUN
###########################################

if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
