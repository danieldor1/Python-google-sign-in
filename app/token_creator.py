import uuid
import jwt
import os

from typing import Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.config import KeysManagerInvokator


ENCRYPTION_ALGORITHM = KeysManagerInvokator.encryption_algorithm.value
ENCRYPTION_ALGORITHM_SECRET_KEY = KeysManagerInvokator.encryption_secret_key.value


class DataPayloadTokenCreation(BaseModel):

    email: str
    id: int
    user_id: int


class TokenCreatorForAuthFlow:

    def __init__(
        self,
    ):

        self.secret_key = ENCRYPTION_ALGORITHM_SECRET_KEY
        self.algorithm = ENCRYPTION_ALGORITHM

    def creator_unique_alphanumeric_with_uuid(
        self
    ) -> str:

        unique_token = str(uuid.uuid4())

        return unique_token

    def _wrapper_create_access_token(
        self,
        data_payload: Dict[str, Any],
        expires_delta: timedelta = None
    ) -> str:

        dict_of_data_to_encode = data_payload.copy()
        expire_parameter = datetime.utcnow() + (expires_delta)

        dict_of_data_to_encode.update({
            "token_expiration_datetime": str(expire_parameter),
        })

        encoded_jwt = jwt.encode(
            payload=dict_of_data_to_encode,
            key=self.secret_key,
            algorithm=self.algorithm
        )

        return encoded_jwt

    def _generator_jwt_token(
        self,
        payload_to_encode: DataPayloadTokenCreation
    ) -> str:

        datetime.utcnow()
        token_event_id = self.creator_unique_alphanumeric_with_uuid()
        registration_token_expires_parameter = timedelta(weeks=2)

        registration_token_data = {
            "user_id": payload_to_encode.user_id,
            "google_id": payload_to_encode.id,
            "user_email": payload_to_encode.email,
            "token_creation_datetime": str(datetime.utcnow()),
            "event_id": token_event_id
        }

        return self._wrapper_create_access_token(
            data_payload=registration_token_data,
            expires_delta=registration_token_expires_parameter)

    def _create_token_to_client(
        self,
        payload: DataPayloadTokenCreation
    ) -> str:

        resulting_token = self._generator_jwt_token(
            payload_to_encode=payload
        )

        return resulting_token

    def _common_logic_handler_return_response(
        self,
        inputs: Dict[Any, Any]
    ) -> str:

        resulting_token = self._create_token_to_client(
            DataPayloadTokenCreation(**inputs)
        )

        return resulting_token

    @classmethod
    def create_token(
        cls,
        payload_to_encript: DataPayloadTokenCreation
    ) -> str:

        instance = cls()

        return instance._common_logic_handler_return_response({
            "id": payload_to_encript['id'],
            "email": payload_to_encript['email'],
            "user_id": payload_to_encript['user_id']
        })


##################################################################
# TEST ZONE
##################################################################
# Example usage
# payload_data = {
#    "email": "1234q5223222wwwwexample@gmail.com",
#    "family_name": "Doe",
#    "user_id": 121,
#    "given_name": "John",
#    "id": 12311143411112123,
#    "locale": "en_US",
#    "name": "John Doe",
#    "picture": "https://example.com/profile_picture.jpg",
#    "verified_email": True
# 
#
# token = TokenCreatorForAuthFlow.create_token(
#    payload_to_encript=payload_data)
# print(token)
