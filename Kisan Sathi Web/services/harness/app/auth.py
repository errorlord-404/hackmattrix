from __future__ import annotations

from collections.abc import Mapping

from kisansathi_auth.csrf import CsrfError, CsrfTokenCodec, require_csrf
from kisansathi_auth.claims import ActorScope

from .sessions import HarnessSession, SessionManager, SessionOwnershipError


class HarnessAuthError(PermissionError):
    def __init__(self, code: str = "authentication_required") -> None:
        super().__init__(code)
        self.code = code


def authenticate_request(
    manager: SessionManager,
    *,
    cookies: Mapping[str, str] | None,
    headers: Mapping[str, str] | None,
    method: str = "GET",
    expected_session_id: str | None = None,
    csrf: CsrfTokenCodec | None = None,
) -> HarnessSession:
    """Verify the same signed cookie/CSRF contract as the API.

    ActorScope is always decoded from the signed server cookie. A caller-provided
    actor object is intentionally not accepted by this function.
    """

    cookies = cookies or {}
    headers = headers or {}
    cookie = cookies.get("kisansathi_session") or cookies.get("session")
    if not cookie:
        raise HarnessAuthError()
    try:
        session = manager.verify_cookie(cookie, expected_session_id=expected_session_id)
        csrf_codec = csrf or CsrfTokenCodec(manager.codec.keys[manager.codec.active_kid])
        require_csrf(method, cookie, cookies.get("kisansathi_csrf"), headers.get("X-CSRF-Token"), csrf=csrf_codec, session_id=session.session_id)
        return session
    except (SessionOwnershipError, CsrfError) as exc:
        raise HarnessAuthError("session_forbidden") from exc


def assert_actor_owned(session: HarnessSession, actor: ActorScope) -> None:
    if session.actor != actor:
        raise HarnessAuthError("session_forbidden")
