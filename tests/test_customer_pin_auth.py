"""Unit tests for CustomerAuthService core behaviour.

Task 9.1 — Requirements: 2.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.5, 4.7, 8.1

Each test uses the ``isolated_sqlite_db`` autouse fixture defined in
``conftest.py``, which redirects ``customer_auth_service._db_path`` to a
fresh per-test SQLite database and calls ``storage.init_db()`` so all tables
(including ``customer_auth`` and ``mock_accounts``) are present and seeded
with the three demo accounts before the test body runs.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.customer_auth import CustomerAuthService, PinVerifyResult, customer_auth_service
from backend.storage import CUSTOMER_AUTH_TABLE, DB_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The demo accounts are seeded by init_db() via _seed_mock_utility_data().
DEMO_ACCOUNT = "000001"
DEMO_PIN = "1234"
OTHER_ACCOUNT = "000002"
OTHER_PIN = "5678"


def _get_auth_row(db_path, account_number: str):
    """Return the customer_auth row for *account_number*, or None."""
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            f"SELECT pin_salt, pin_hash, failed_attempts, locked_until "
            f"FROM {CUSTOMER_AUTH_TABLE} WHERE account_number = ?",
            (account_number,),
        ).fetchone()


def _set_locked(db_path, account_number: str, locked_until: datetime, failed_attempts: int = 3):
    """Directly write a locked state into customer_auth for testing."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"UPDATE {CUSTOMER_AUTH_TABLE} "
            f"SET failed_attempts = ?, locked_until = ? "
            f"WHERE account_number = ?",
            (failed_attempts, locked_until.isoformat(), account_number),
        )


def _set_failed_attempts(db_path, account_number: str, failed_attempts: int):
    """Directly set failed_attempts without locking."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"UPDATE {CUSTOMER_AUTH_TABLE} "
            f"SET failed_attempts = ?, locked_until = NULL "
            f"WHERE account_number = ?",
            (failed_attempts, account_number),
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetPin:
    """Tests for CustomerAuthService.set_pin()."""

    def test_set_pin_stores_hash_not_plaintext(self):
        """Requirement 2.2 — stored pin_hash must not equal the plaintext PIN.

        The hash is a PBKDF2-SHA256 hex digest; it can never equal the 4-digit
        plaintext string.
        """
        svc = customer_auth_service
        db_path = svc._db_path

        svc.set_pin(DEMO_ACCOUNT, DEMO_PIN)

        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row is not None, "customer_auth row should exist after set_pin"
        _pin_salt, pin_hash, _failed, _locked = row

        # The stored hash must not be the plaintext PIN.
        assert pin_hash != DEMO_PIN, (
            "pin_hash must not equal the plaintext PIN"
        )
        # The hash should be a 64-character hex string (SHA-256 digest).
        assert len(pin_hash) == 64, "PBKDF2-SHA256 hex digest should be 64 chars"
        assert all(c in "0123456789abcdef" for c in pin_hash), (
            "pin_hash should be a lowercase hex string"
        )


class TestVerifyPin:
    """Tests for CustomerAuthService.verify_pin()."""

    def test_verify_pin_correct(self):
        """Requirement 3.3, 3.5 — correct PIN returns success=True."""
        svc = customer_auth_service
        # Demo PIN is seeded by init_db(); verify it works.
        result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)

        assert isinstance(result, PinVerifyResult)
        assert result.success is True
        assert result.locked is False
        assert result.locked_until is None

    def test_verify_pin_wrong(self):
        """Requirement 4.1 — wrong PIN returns success=False and increments counter."""
        svc = customer_auth_service
        wrong_pin = "0000"

        result = svc.verify_pin(DEMO_ACCOUNT, wrong_pin)

        assert result.success is False
        assert result.locked is False
        # After 1 failure, 2 attempts remain.
        assert result.remaining_attempts == 2

    def test_verify_pin_correct_resets_failed_attempts(self):
        """Requirement 3.5, 4.5 — successful verification resets failed_attempts to 0."""
        svc = customer_auth_service
        db_path = svc._db_path

        # Manually set failed_attempts to 2 (not yet locked).
        _set_failed_attempts(db_path, DEMO_ACCOUNT, 2)

        result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)

        assert result.success is True
        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row is not None
        _salt, _hash, failed_attempts, locked_until = row
        assert failed_attempts == 0, "failed_attempts should be reset to 0 on success"
        assert locked_until is None, "locked_until should be NULL on success"


class TestLockout:
    """Tests for account lockout behaviour (Requirement 4.x)."""

    def test_lockout_after_3_failures(self):
        """Requirement 4.1, 4.2 — 3rd failure sets locked_until ≈ now+15min."""
        svc = customer_auth_service
        db_path = svc._db_path
        wrong_pin = "0000"

        # First two failures should not lock.
        r1 = svc.verify_pin(DEMO_ACCOUNT, wrong_pin)
        assert r1.success is False and r1.locked is False
        r2 = svc.verify_pin(DEMO_ACCOUNT, wrong_pin)
        assert r2.success is False and r2.locked is False

        # Third failure should trigger lockout.
        before = datetime.now(timezone.utc)
        r3 = svc.verify_pin(DEMO_ACCOUNT, wrong_pin)
        after = datetime.now(timezone.utc)

        assert r3.success is False
        assert r3.locked is True
        assert r3.locked_until is not None

        # locked_until should be approximately now + 15 minutes.
        locked_until_dt = datetime.fromisoformat(r3.locked_until)
        if locked_until_dt.tzinfo is None:
            locked_until_dt = locked_until_dt.replace(tzinfo=timezone.utc)

        expected_min = before + timedelta(minutes=14, seconds=59)
        expected_max = after + timedelta(minutes=15, seconds=1)
        assert expected_min <= locked_until_dt <= expected_max, (
            f"locked_until {locked_until_dt} should be ≈ now+15min "
            f"(expected between {expected_min} and {expected_max})"
        )

        # Verify the DB row reflects the lock.
        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row is not None
        _salt, _hash, failed_attempts, locked_until_str = row
        assert failed_attempts == 3
        assert locked_until_str is not None

    def test_locked_account_rejects_correct_pin(self):
        """Requirement 4.3 — correct PIN is rejected while account is locked."""
        svc = customer_auth_service
        db_path = svc._db_path

        # Lock the account directly (15 minutes in the future).
        future = datetime.now(timezone.utc) + timedelta(minutes=15)
        _set_locked(db_path, DEMO_ACCOUNT, future, failed_attempts=3)

        result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)

        assert result.success is False
        assert result.locked is True
        assert result.locked_until is not None
        # Counter must NOT be incremented while locked.
        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row[2] == 3, "failed_attempts must not change while account is locked"

    def test_lockout_expires(self):
        """Requirement 4.5 — after locked_until passes, correct PIN succeeds."""
        svc = customer_auth_service
        db_path = svc._db_path

        # Set locked_until to a time in the past (lock has expired).
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        _set_locked(db_path, DEMO_ACCOUNT, past, failed_attempts=3)

        result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)

        assert result.success is True, (
            "Correct PIN should succeed after lock has expired"
        )
        assert result.locked is False

        # failed_attempts should be reset to 0 after successful verification.
        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row[2] == 0, "failed_attempts should be reset to 0 after lock expires and PIN succeeds"
        assert row[3] is None, "locked_until should be NULL after successful verification"


class TestAdminReset:
    """Tests for CustomerAuthService.reset_pin()."""

    def test_admin_reset_unlocks_account(self):
        """Requirement 4.7 — reset_pin() on a locked account clears the lock."""
        svc = customer_auth_service
        db_path = svc._db_path

        # Lock the account.
        future = datetime.now(timezone.utc) + timedelta(minutes=15)
        _set_locked(db_path, DEMO_ACCOUNT, future, failed_attempts=3)

        # Verify it is locked before reset.
        locked_result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)
        assert locked_result.locked is True, "Account should be locked before reset"

        # Admin resets the PIN.
        new_pin = "9999"
        svc.reset_pin(DEMO_ACCOUNT, new_pin)

        # The account should now be unlocked.
        row = _get_auth_row(db_path, DEMO_ACCOUNT)
        assert row is not None
        _salt, _hash, failed_attempts, locked_until = row
        assert failed_attempts == 0, "failed_attempts should be 0 after admin reset"
        assert locked_until is None, "locked_until should be NULL after admin reset"

        # The new PIN should work.
        result = svc.verify_pin(DEMO_ACCOUNT, new_pin)
        assert result.success is True, "New PIN should verify successfully after reset"

        # The old PIN should no longer work.
        old_result = svc.verify_pin(DEMO_ACCOUNT, DEMO_PIN)
        assert old_result.success is False, "Old PIN should be rejected after reset"

    def test_admin_reset_writes_audit_log(self):
        """Requirement 6.8 — reset_pin() writes an audit log entry on success."""
        svc = customer_auth_service
        db_path = svc._db_path

        with sqlite3.connect(db_path) as conn:
            before_count = conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action = 'pin_reset'"
            ).fetchone()[0]

        svc.reset_pin(DEMO_ACCOUNT, "7777")

        with sqlite3.connect(db_path) as conn:
            after_count = conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action = 'pin_reset'"
            ).fetchone()[0]

        assert after_count == before_count + 1, (
            "An audit_logs entry should be created for every successful reset_pin call"
        )


class TestMigrationAndSeeding:
    """Tests for storage migration and demo PIN seeding (Task 9.2).
    Requirements: 1.4, 1.7, 7.1, 7.2, 7.3, 7.4
    """

    def test_migration_account_numbers(self, monkeypatch, tmp_path):
        """Old account numbers are renamed and FK references updated."""
        # Use a fresh isolated DB
        import sqlite3
        from backend import storage
        from backend.customer_auth import customer_auth_service

        test_db = tmp_path / "migration_test.db"
        monkeypatch.setattr(storage, "DB_PATH", test_db)
        monkeypatch.setattr(customer_auth_service, "_db_path", test_db)

        # Seed old-format accounts directly before init_db runs migration
        with sqlite3.connect(test_db) as conn:
            # Create tables manually first
            storage.init_db()  # creates tables + seeds new format

        # After init_db, accounts should be in new format
        with sqlite3.connect(test_db) as conn:
            accts = [r[0] for r in conn.execute("SELECT account_number FROM mock_accounts").fetchall()]
        assert "000001" in accts
        assert "000002" in accts
        assert "000003" in accts
        assert "123456" not in accts
        assert "789012" not in accts
        assert "555666" not in accts

        # FK references in mock_bills should use new account numbers
        with sqlite3.connect(test_db) as conn:
            bill_accts = [r[0] for r in conn.execute("SELECT DISTINCT account_number FROM mock_bills").fetchall()]
        for old in ["123456", "789012", "555666"]:
            assert old not in bill_accts

    def test_demo_pin_seeding(self):
        """Demo PINs work after init_db() (Requirements 7.3, 7.5)."""
        svc = customer_auth_service
        # init_db() is called by the isolated_sqlite_db fixture
        assert svc.verify_pin("000001", "1234").success is True
        assert svc.verify_pin("000002", "5678").success is True
        assert svc.verify_pin("000003", "9012").success is True

    def test_demo_pin_not_overwritten(self, monkeypatch, tmp_path):
        """Re-running init_db() does not overwrite changed PINs (Requirement 7.3)."""
        from backend import storage
        from backend.customer_auth import customer_auth_service

        test_db = tmp_path / "no_overwrite_test.db"
        monkeypatch.setattr(storage, "DB_PATH", test_db)
        monkeypatch.setattr(customer_auth_service, "_db_path", test_db)

        storage.init_db()  # seeds demo PINs

        # Change the PIN for account 000001
        customer_auth_service.set_pin("000001", "9999")
        assert customer_auth_service.verify_pin("000001", "9999").success is True

        # Re-run init_db() — should NOT overwrite the changed PIN
        storage.init_db()

        # The changed PIN should still work
        assert customer_auth_service.verify_pin("000001", "9999").success is True
        # The original demo PIN should no longer work
        assert customer_auth_service.verify_pin("000001", "1234").success is False

    def test_account_number_exhaustion(self, monkeypatch, tmp_path):
        """next_account_number() raises ValueError at 999999 (Requirement 1.7)."""
        import sqlite3
        from backend import storage
        from backend.customer_auth import customer_auth_service

        test_db = tmp_path / "exhaustion_test.db"
        monkeypatch.setattr(storage, "DB_PATH", test_db)
        monkeypatch.setattr(customer_auth_service, "_db_path", test_db)
        storage.init_db()

        # Insert a row with account_number = 999999
        with sqlite3.connect(test_db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mock_accounts(account_number, customer_id, area, address, meter_number, status) "
                "VALUES ('999999', 'CUST-MAX', 'Test', 'Test Address', 'MTR-MAX', 'ACTIVE')"
            )
            with pytest.raises(ValueError, match="999999"):
                storage.next_account_number(conn)


class TestAdminResetEndpoint:
    """Tests for POST /admin/accounts/{account_number}/reset-pin (Task 9.3).
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
    """

    def test_admin_reset_endpoint_401(self):
        """Missing token → HTTP 401."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post("/admin/accounts/000001/reset-pin", json={"new_pin": "9999"})
        assert resp.status_code == 401

    def test_admin_reset_endpoint_404(self):
        """Unknown account → HTTP 404."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/admin/accounts/999999/reset-pin",
            json={"new_pin": "9999"},
            headers={"Authorization": "Bearer test-admin-token"},
        )
        assert resp.status_code == 404

    def test_admin_reset_endpoint_422(self):
        """Invalid PIN format → HTTP 422."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/admin/accounts/000001/reset-pin",
            json={"new_pin": "abc"},
            headers={"Authorization": "Bearer test-admin-token"},
        )
        assert resp.status_code == 422

    def test_admin_reset_endpoint_200(self):
        """Valid request → HTTP 200 + correct body."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/admin/accounts/000001/reset-pin",
            json={"new_pin": "9999"},
            headers={"Authorization": "Bearer test-admin-token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["account_number"] == "000001"

    def test_audit_log_on_reset_success(self):
        """Audit log entry created on successful reset (Requirement 6.8)."""
        import sqlite3
        from fastapi.testclient import TestClient
        from main import app
        from backend.customer_auth import customer_auth_service

        db_path = customer_auth_service._db_path
        client = TestClient(app)

        with sqlite3.connect(db_path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='pin_reset'").fetchone()[0]

        client.post(
            "/admin/accounts/000001/reset-pin",
            json={"new_pin": "8888"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

        with sqlite3.connect(db_path) as conn:
            after = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='pin_reset'").fetchone()[0]

        assert after == before + 1

    def test_audit_log_on_reset_failure(self):
        """Audit log entry created even on validation failure (Requirement 6.8)."""
        import sqlite3
        from fastapi.testclient import TestClient
        from main import app
        from backend.customer_auth import customer_auth_service

        db_path = customer_auth_service._db_path
        client = TestClient(app)

        with sqlite3.connect(db_path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'pin_reset%'").fetchone()[0]

        # Invalid PIN format — should fail but still log
        client.post(
            "/admin/accounts/000001/reset-pin",
            json={"new_pin": "bad"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

        with sqlite3.connect(db_path) as conn:
            after = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'pin_reset%'").fetchone()[0]

        assert after == before + 1


class TestBillingAgentPinFlow:
    """Tests for BillingAgent PIN flow edge cases (Task 9.4).
    Requirements: 8.4
    """

    def test_pin_prompt_excludes_account_number(self):
        """PIN prompt reply must not contain the account number (Requirement 8.4)."""
        from fastapi.testclient import TestClient
        from main import app
        from backend.customer_auth import customer_auth_service

        # Seed a PIN so the account is set up
        customer_auth_service.set_pin("000001", "1234")

        client = TestClient(app)
        user_id = "pin-prompt-test-user"
        client.post("/chat/clear", json={"user_id": user_id})

        # Step 1: billing intent — bot asks for account number
        client.post("/chat", json={"user_id": user_id, "message": "I want to check my bill"})

        # Step 2: provide account number — bot should ask for PIN
        resp = client.post("/chat", json={"user_id": user_id, "message": "000001"})
        body = resp.json()

        assert resp.status_code == 200
        reply = body["response"]
        # The reply should ask for PIN
        assert "pin" in reply.lower(), f"Expected PIN prompt, got: {reply!r}"
        # The reply must NOT contain the account number
        assert "000001" not in reply, (
            f"PIN prompt must not reveal the account number, but got: {reply!r}"
        )
