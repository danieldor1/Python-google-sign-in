#################################################
# -*- coding: utf-8 -*-
#################################################
# MAIN ENTRYPOINT
#################################################
import os
import requests

from pathlib import Path
from starlette.requests import Request
from google_auth_oauthlib.flow import Flow
from fastapi.responses import RedirectResponse
from fastapi import HTTPException, status, FastAPI, Header
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.tokens_verify import verify_user
from app.response import deeplink_response_generator
from app.interactions_db import create_session_google, create_user_google
from app.token_creator import TokenCreatorForAuthFlow
from app.config import KeysManagerInvokator

app = FastAPI()
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# URL FOR CALLBACK
GOOGLE_CLIENT_ID = KeysManagerInvokator.client_id.value
GOOGLE_REDIRECT_URI = KeysManagerInvokator.redirect_url.value
URL = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

client_secrets_file = Path(__file__).parent / "client_secret.json"

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=SCOPES,
    redirect_uri=GOOGLE_REDIRECT_URI
)


@app.post("/verify-token")
async def verify_token(authorization: str = Header(...)):
    """
    Verify the validity of a token extracted from the authorization header
    """
    try:
        if authorization.startswith("Bearer "):
            token = str(authorization.split("Bearer ")[1])
            response = await verify_user(token=token)
            return {"status": response}

        # Raise an exception for invalid authorization header
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header please include a Bearer token."
            )
    except HTTPException as e:
        # Catch any HTTP exceptions and return a response with the detail
        return {"status": e.detail}


##################################################
# REGISTER: ENDPOINT FOR GOOGLE/ACCESS CALLBACK 
##################################################

@app.get('/login/google')
async def login_google():
    return {"url": URL}


@app.get('/oauth2callback')
async def oauth2callback(code:str, request: Request):
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

        return deeplink_response_generator(
            code_from_db=response_status_code_from_the_session_db,
            returned_token=returned_token
        )

    except Exception:
        deeplink_url = f'app_deeplink://status=login_failed&error_code=500'
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
