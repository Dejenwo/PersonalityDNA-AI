from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# The API serves JSON (and a few downloads); it never needs to run scripts or be framed.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
HSTS = "max-age=63072000; includeSubDomains"
PUBLIC = "/api/v1/public/"
DOCS = ("/docs", "/redoc")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, hsts: bool = False) -> None:
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        path = request.url.path
        # Public share cards may be shown by other sites (social previews); everything else stays same-site.
        corp = "cross-origin" if path.startswith(PUBLIC) else "same-site"
        h.setdefault("Cross-Origin-Resource-Policy", corp)
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        if not path.startswith(DOCS):  # the development API explorer loads its own scripts
            h.setdefault("Content-Security-Policy", API_CSP)
        if self.hsts:
            # Only behind TLS (staging and production); browsers ignore it over plain HTTP anyway.
            h.setdefault("Strict-Transport-Security", HSTS)
        if path.startswith("/api/"):
            # Assessment data is personal; never cache API responses in shared caches.
            h.setdefault("Cache-Control", "no-store")
        return response
