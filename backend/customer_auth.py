"""backend/customer_auth.py

Customer-level PIN authentication for the Kabwe Water agentic chatbot.

This module provides:
- Secure PIN storage (PBKDF2-SHA256, salted, constant-time comparison)
- PIN verification with account lockout after 3 consecutive failures
- Admin-initiated PIN reset with audit logging
- Input validation for account numbers and PIN format

Mirrors the structure of ``backend/auth.py`` (``AuthService``) for consistency.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import sqlite3

from .logger import logger
from .storage import DB_PATH, CUSTOMER_AUTH_TABLE, ACCOUNTS_TABLE


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PinVerifyResult:
    """Result returned by :meth:`CustomerAuthService.verify_pin`.

    Attributes:
        success: ``True`` when the candidate PIN matched the stored hash.
        locked: ``True`` when the account is currently locked out.
        locked_until: ISO 8601 UTC timestamp string indicating when the lock
            expires, or ``None`` when the account is not locked.
        remaining_attempts: Number of attempts left before lockout (0–2 on
            failure); ``None`` when the account is locked or verification
            succeeded.
    """

    success: bool
    locked: bool
    locked_until: Optional[str]       # ISO 8601 UTC, or None
    remaining_attempts: Optional[int]  # None when locked or success


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class CustomerAuthService:
    """Manages customer PIN authentication against the ``customer_auth`` table.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Defaults to the same path used by
        ``storage.py`` (``DB_PATH``).  Pass a different path in tests to get
        an isolated database.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path: Path = Path(db_path) if db_path is not None else DB_PATH

    # ------------------------------------------------------------------
    # Internal connection helper
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the configured database file."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_account_number(self, account_number: str) -> None:
        """Raise ``ValueError`` if *account_number* is not exactly 6 decimal digits.

        Raises
        ------
        ValueError
            With the message ``"account_number must be exactly 6 decimal digits"``.
        """
        if not re.fullmatch(r"[0-9]{6}", account_number or ""):
            raise ValueError("account_number must be exactly 6 decimal digits")

    def _validate_pin_format(self, pin: str) -> None:
        """Raise ``ValueError`` if *pin* is not exactly 4 decimal digits.

        Raises
        ------
        ValueError
            With the message ``"PIN must be exactly 4 decimal digits"``.
        """
        if not re.fullmatch(r"[0-9]{4}", pin or ""):
            raise ValueError("PIN must be exactly 4 decimal digits")

    def _hash_pin(self, pin: str, salt_hex: str) -> str:
        """Derive a PIN hash using PBKDF2-SHA256.

        Parameters
        ----------
        pin:
            The plaintext 4-digit PIN string.
        salt_hex:
            A 64-character hexadecimal string representing 32 random bytes.

        Returns
        -------
        str
            The 64-character hexadecimal digest.
        """
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode(),
            bytes.fromhex(salt_hex),
            260_000,
        )
        return digest.hex()

    def _log_security_event(
        self,
        action: str,
        account_number: str,
        details: Dict[str, Any],
    ) -> None:
        """Insert an audit log entry into ``audit_logs``.

        Mirrors the pattern used by ``AuthService._log_security_event`` in
        ``auth.py``.  The ``audit_logs`` table is created by
        ``AuthService._init_audit_tables()`` which runs at import time via the
        module-level ``auth_service`` singleton.
        """
        log_id = f"CAUD_{secrets.token_hex(12)}"
        timestamp = datetime.now(timezone.utc).isoformat()
        user_id = details.get("user_id", "system")

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs
                        (log_id, user_id, action, resource, timestamp,
                         ip_address, user_agent, success, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log_id,
                        user_id,
                        action,
                        f"customer_auth:{account_number}",
                        timestamp,
                        None,   # ip_address — not available at this layer
                        None,   # user_agent — not available at this layer
                        details.get("success", True),
                        str(details),
                    ),
                )
        except sqlite3.Error as exc:
            # Audit logging must never crash the caller.
            logger.warning(
                "customer_auth.audit_log_failed",
                extra={"extra_data": {"error": str(exc), "action": action}},
            )

        logger.warning(
            f"security.customer_auth.{action}",
            extra={"extra_data": {"account_number": account_number, **details}},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pin(self, account_number: str, pin: str) -> None:
        """Hash and store a PIN for *account_number*.

        Validates inputs, verifies the account exists in ``mock_accounts``,
        generates a fresh random salt, hashes the PIN with PBKDF2-SHA256, and
        upserts the row in ``customer_auth`` with ``failed_attempts=0`` and
        ``locked_until=NULL``.

        Parameters
        ----------
        account_number:
            Must be exactly 6 decimal digits.
        pin:
            Must be exactly 4 decimal digits.

        Raises
        ------
        ValueError
            If *account_number* is not exactly 6 decimal digits.
        ValueError
            If *pin* is not exactly 4 decimal digits.
        ValueError
            If *account_number* does not exist in ``mock_accounts``.
        """
        self._validate_account_number(account_number)
        self._validate_pin_format(pin)

        with self._connect() as conn:
            row = conn.execute(
                f"SELECT 1 FROM {ACCOUNTS_TABLE} WHERE account_number = ?",
                (account_number,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Account {account_number} not found")

            salt_hex = os.urandom(32).hex()
            pin_hash = self._hash_pin(pin, salt_hex)

            conn.execute(
                f"""
                INSERT OR REPLACE INTO {CUSTOMER_AUTH_TABLE}
                    (account_number, pin_salt, pin_hash, failed_attempts, locked_until)
                VALUES (?, ?, ?, 0, NULL)
                """,
                (account_number, salt_hex, pin_hash),
            )

    def verify_pin(self, account_number: str, candidate_pin: str) -> PinVerifyResult:
        """Verify *candidate_pin* against the stored hash for *account_number*.

        Behaviour:
        - Uses ``hmac.compare_digest`` for constant-time comparison.
        - Returns a "no PIN set" failure result when no row exists yet.
        - Rejects all attempts (without incrementing the counter) while locked.
        - Increments ``failed_attempts`` on each failure.
        - Sets ``locked_until = now + 15 min`` when ``failed_attempts`` reaches 3.
        - Resets ``failed_attempts = 0`` and ``locked_until = NULL`` on success.

        Parameters
        ----------
        account_number:
            Must be exactly 6 decimal digits.
        candidate_pin:
            The PIN string submitted by the customer (any value; format is not
            validated here so that the caller receives a clean failure result
            rather than a ``ValueError`` for a wrong-format guess).

        Returns
        -------
        PinVerifyResult

        Raises
        ------
        ValueError
            If *account_number* is not exactly 6 decimal digits.
        """
        self._validate_account_number(account_number)

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT pin_salt, pin_hash, failed_attempts, locked_until
                FROM {CUSTOMER_AUTH_TABLE}
                WHERE account_number = ?
                """,
                (account_number,),
            ).fetchone()

            # No PIN has been set yet — treat as wrong PIN with full attempts remaining.
            if row is None:
                return PinVerifyResult(
                    success=False,
                    locked=False,
                    locked_until=None,
                    remaining_attempts=3,
                )

            pin_salt, pin_hash, failed_attempts, locked_until_str = row

            # Check lockout status.
            now_utc = datetime.now(timezone.utc)
            if locked_until_str is not None:
                try:
                    locked_until_dt = datetime.fromisoformat(locked_until_str)
                    # Ensure timezone-aware comparison.
                    if locked_until_dt.tzinfo is None:
                        locked_until_dt = locked_until_dt.replace(tzinfo=timezone.utc)
                    if now_utc < locked_until_dt:
                        # Still locked — do NOT increment counter.
                        return PinVerifyResult(
                            success=False,
                            locked=True,
                            locked_until=locked_until_str,
                            remaining_attempts=None,
                        )
                except ValueError:
                    # Malformed timestamp — treat as expired lock.
                    pass

            # Hash the candidate and compare in constant time.
            candidate_hash = self._hash_pin(candidate_pin, pin_salt)
            match = hmac.compare_digest(candidate_hash, pin_hash)

            if match:
                conn.execute(
                    f"""
                    UPDATE {CUSTOMER_AUTH_TABLE}
                    SET failed_attempts = 0, locked_until = NULL
                    WHERE account_number = ?
                    """,
                    (account_number,),
                )
                return PinVerifyResult(
                    success=True,
                    locked=False,
                    locked_until=None,
                    remaining_attempts=None,
                )

            # Wrong PIN — increment counter.
            new_failed = failed_attempts + 1
            if new_failed >= 3:
                lock_until_dt = now_utc + timedelta(minutes=15)
                lock_until_str = lock_until_dt.isoformat()
                conn.execute(
                    f"""
                    UPDATE {CUSTOMER_AUTH_TABLE}
                    SET failed_attempts = ?, locked_until = ?
                    WHERE account_number = ?
                    """,
                    (new_failed, lock_until_str, account_number),
                )
                return PinVerifyResult(
                    success=False,
                    locked=True,
                    locked_until=lock_until_str,
                    remaining_attempts=None,
                )

            conn.execute(
                f"""
                UPDATE {CUSTOMER_AUTH_TABLE}
                SET failed_attempts = ?
                WHERE account_number = ?
                """,
                (new_failed, account_number),
            )
            return PinVerifyResult(
                success=False,
                locked=False,
                locked_until=None,
                remaining_attempts=3 - new_failed,
            )

    def reset_pin(self, account_number: str, new_pin: str) -> None:
        """Admin-initiated PIN reset.

        Validates inputs, logs a security event (both before and after the
        operation to record the outcome), then delegates to :meth:`set_pin`.

        Parameters
        ----------
        account_number:
            Must be exactly 6 decimal digits.
        new_pin:
            Must be exactly 4 decimal digits.

        Raises
        ------
        ValueError
            For the same conditions as :meth:`set_pin`.
        """
        # Validate eagerly so the audit log captures the failure reason.
        try:
            self._validate_account_number(account_number)
            self._validate_pin_format(new_pin)
        except ValueError as exc:
            self._log_security_event(
                "pin_reset_failed",
                account_number,
                {"reason": str(exc), "success": False},
            )
            raise

        try:
            self.set_pin(account_number, new_pin)
        except ValueError as exc:
            self._log_security_event(
                "pin_reset_failed",
                account_number,
                {"reason": str(exc), "success": False},
            )
            raise

        self._log_security_event(
            "pin_reset",
            account_number,
            {"success": True},
        )


# ---------------------------------------------------------------------------
# Module-level singleton (mirrors ``auth_service`` in ``auth.py``)
# ---------------------------------------------------------------------------

customer_auth_service = CustomerAuthService()
