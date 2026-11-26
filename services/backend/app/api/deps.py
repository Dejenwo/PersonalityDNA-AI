from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.assessments.content import ContentBundle


def get_db(request: Request) -> Iterator[Session]:
    yield from request.app.state.db.session()


def get_content(request: Request) -> ContentBundle:
    bundle: ContentBundle = request.app.state.content
    return bundle


def client_ip(request: Request) -> str:
    # Behind a proxy, configure uvicorn --proxy-headers with trusted --forwarded-allow-ips
    # so request.client reflects the real client. Never trust X-Forwarded-For directly here.
    return request.client.host if request.client else "unknown"
