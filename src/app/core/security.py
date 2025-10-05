from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self';"
            " script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/ https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js;"
            " style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/ https://fonts.googleapis.com/;"
            " font-src 'self' https://fonts.gstatic.com/;"
            " img-src 'self' data: https://fastapi.tiangolo.com;"
            " object-src 'none';"
            " frame-ancestors 'none';"
            " connect-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css.map https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js.map;"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response