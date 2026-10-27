"""Lifetime of the existing JEVKEY source during serial campaign dispatch.

No persistence, discovery, child inheritance or read before authenticated broker
readiness. This process is the trusted launcher, never the assessment worker.
"""
from contextlib import contextmanager
import os

from ..systemone_https_v1.credential import harden, validate

_token = None
_active = False


def configured():
    return _token is not None or "JEVKEY" in os.environ


def issue():
    global _token
    if not _active:
        raise ValueError("campaign_credential_lifetime_not_active")
    harden()
    if _token is None:
        value = os.environ.pop("JEVKEY", None)
        if value is None:
            raise ValueError("JEVKEY_not_configured")
        try:
            _token = bytearray(value.strip().encode("ascii"))
        except (UnicodeError, AttributeError):
            raise ValueError("JEVKEY_invalid_encoding") from None
        finally:
            del value
        validate(_token)
    return bytearray(_token)


@contextmanager
def session():
    global _active, _token
    if _active:
        raise ValueError("campaign_credential_session_already_active")
    _active = True
    try:
        yield
    finally:
        if _token is not None:
            _token[:] = b"\x00" * len(_token)
        _token, _active = None, False
