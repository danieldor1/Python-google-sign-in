from app.schemas import HttpResponseFromDb
from fastapi.responses import RedirectResponse


def deeplink_response_generator(code_from_db: str, returned_token: str)-> RedirectResponse:
    if code_from_db == HttpResponseFromDb.DB_ACCESS_POINT_REGISTER_SUCCESS.value:
        deeplink_url = f'app_deeplink://status=created&token={returned_token}'

    elif code_from_db == HttpResponseFromDb.ACCESS_POINT_INTERNAL_SERVER_ERROR.value:
        deeplink_url = 'app_deeplink://status=login_failed&token=false'
          
    elif code_from_db == HttpResponseFromDb.DB_ACCESS_POINT_ALREADY_REGISTERED_CONFLICT.value:
        deeplink_url = f'app_deeplink://status=authenticated&token={returned_token}'

    return RedirectResponse(
        url=deeplink_url)

