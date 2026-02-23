from fastapi.encoders import jsonable_encoder
from fastapi.error_enhancement import enhance_errors
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from fastapi.websockets import WebSocket
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import WS_1008_POLICY_VIOLATION


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    headers = getattr(exc, "headers", None)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    return JSONResponse(
        {"detail": exc.detail}, status_code=exc.status_code, headers=headers
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Enhance validation errors with field path, examples, and suggestions
    errors = exc.errors()
    enhanced_errors = enhance_errors(errors)
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(enhanced_errors)},
    )


async def websocket_request_validation_exception_handler(
    websocket: WebSocket, exc: WebSocketRequestValidationError
) -> None:
    # Enhance validation errors with field path, examples, and suggestions
    errors = exc.errors()
    enhanced_errors = enhance_errors(errors)
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION, reason=jsonable_encoder(enhanced_errors)
    )
