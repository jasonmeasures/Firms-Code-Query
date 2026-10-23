"""Who may see a request, and who may load a whole reference file.

OPERATOR sees only requests they created. ADMIN sees every request, every
orphan, and the vault. Reference rows themselves are shared CHB data: an
operator lookup updates the shared facility row, and both roles can read the
tables. Whole-file loads stay with ADMIN.

tenant_id is stored on requests for a later policy. This build has one tenant.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import ExtractRequest, User

ADMIN_ONLY = {'ALL_DATE', 'ALL_DISTRICT', 'FULL', 'AIR', 'RANGE'}


def requires_admin(query_type: str) -> bool:
    return query_type.upper() in ADMIN_ONLY


def current_user(
    session: Session = Depends(get_session),
    x_demo_user: str | None = Header(default=None),
) -> User:
    settings = get_settings()
    if not settings.is_dev:
        raise HTTPException(status_code=401, detail='Sign-in is not connected yet. Demo users need APP_ENV=dev.')
    user_id = (x_demo_user or 'operator').strip().lower()
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Unknown user')
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail='This reference load is limited to an admin')
    return user


def visible_requests(user: User) -> Select:
    query = select(ExtractRequest).order_by(ExtractRequest.created_at.desc())
    if user.role != 'ADMIN':
        query = query.where(ExtractRequest.requested_by == user.id)
    return query


def can_see(user: User, row: ExtractRequest) -> bool:
    return user.role == 'ADMIN' or row.requested_by == user.id
