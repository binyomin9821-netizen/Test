"""
Field-level encryption for sensitive columns (currently just SSN).

Uses Fernet (symmetric, authenticated encryption) from the `cryptography`
package. The key lives in .env as FIELD_ENCRYPTION_KEY -- never in code,
never in the database. If that key is ever lost, encrypted values can't
be recovered, so back it up somewhere safe, separate from the database
backup itself.
"""
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import LargeBinary, TypeDecorator

from tenant_app import config


def _fernet():
    return Fernet(config.FIELD_ENCRYPTION_KEY.encode())


class EncryptedString(TypeDecorator):
    """A string column that's encrypted at rest. Reads/writes as a plain
    Python str at the ORM layer -- SQLAlchemy handles the conversion."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _fernet().encrypt(value.encode())

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _fernet().decrypt(bytes(value)).decode()
        except InvalidToken:
            # The encryption key changed since this row was written --
            # surface that plainly instead of crashing the page.
            return "[unreadable -- encryption key mismatch]"


def mask_ssn(ssn):
    """Never show a full SSN in the UI. Just the last 4 digits, banking-
    statement style."""
    if not ssn:
        return "—"
    digits = "".join(ch for ch in ssn if ch.isdigit())
    if len(digits) < 4:
        return "•••-••-••••"
    return f"•••-••-{digits[-4:]}"
