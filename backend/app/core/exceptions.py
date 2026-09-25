import logging
import re
import traceback

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("roadsense")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*"
}


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("issue") or detail.get("error") or str(detail)
            error_code = detail.get("error_code") or f"HTTP_{exc.status_code}"
        else:
            message = str(detail)
            error_code = f"HTTP_{exc.status_code}"

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_code": error_code,
                "message": message,
                "detail": message,
                "diagnostic_data": detail if isinstance(detail, dict) else None
            },
            headers=CORS_HEADERS
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        raw_body = None
        try:
            raw_body = await request.body()
        except Exception:
            pass

        error_messages = []
        for err in exc.errors():
            err_type = err.get("type")
            msg = err.get("msg", "Invalid value")
            ctx = err.get("ctx", {})
            ctx_error = ctx.get("error", "")
            if isinstance(ctx_error, Exception):
                ctx_error = str(ctx_error)

            if err_type == "json_invalid":
                loc = err.get("loc", ())
                offset = next((item for item in loc if isinstance(item, int)), None)
                suspect_field = None
                if raw_body and offset is not None:
                    try:
                        prefix = raw_body[:offset].decode("utf-8", errors="replace")
                        keys = re.findall(r'"([a-zA-Z0-9_]+)"\s*:', prefix)
                        if keys:
                            suspect_field = keys[-1]
                    except Exception:
                        pass

                detail_msg = "Malformed JSON syntax in request body"
                if offset is not None:
                    detail_msg += f" at character position {offset}"
                if suspect_field:
                    detail_msg += f" (in or near field '{suspect_field}')"
                if ctx_error:
                    detail_msg += f": {ctx_error}"
                else:
                    detail_msg += f": {msg}"

                if suspect_field in ("password", "new_password", "newPassword") or "control character" in str(ctx_error).lower():
                    detail_msg += ". Please verify that your password or text does not contain raw unescaped line breaks, tabs, or quotes."

                error_messages.append(detail_msg)
            else:
                field = " -> ".join(str(loc) for loc in err.get("loc", []) if loc != "body")
                clean_msg = msg.replace("Value error, ", "")
                error_messages.append(f"{field}: {clean_msg}" if field else clean_msg)

        combined_message = "; ".join(error_messages) or "Validation failed"

        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": f"Validation failed: {combined_message}",
                "detail": combined_message,
                "errors": jsonable_encoder(exc.errors())
            },
            headers=CORS_HEADERS
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, tb)

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": f"Server error: {str(exc)}",
                "detail": f"Server error processing request: {str(exc)}"
            },
            headers=CORS_HEADERS
        )
