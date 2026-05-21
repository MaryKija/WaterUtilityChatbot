# Implementation Plan: customer-pin-auth

## Overview

Implement customer-level PIN authentication for the Kabwe Water agentic WhatsApp bot. The plan
proceeds in five phases: (1) database schema and migration, (2) the `CustomerAuthService` core,
(3) the `BillingAgent` PIN gate in `agent.py`, (4) the admin reset endpoint in `main.py`, and
(5) the full test suite. Each phase builds on the previous one and ends with all code wired
together before moving forward.

---

## Tasks

- [x] 1. Extend `storage.py`: schema, migration, and account-number helpers
  - [x] 1.1 Add `customer_auth` table creation to `init_db()`
    - Inside `init_db()` in `backend/storage.py`, add a `CREATE TABLE IF NOT EXISTS customer_auth`
      block with columns: `account_number TEXT PRIMARY KEY`, `pin_salt TEXT NOT NULL`,
      `pin_hash TEXT NOT NULL`, `failed_attempts INTEGER NOT NULL DEFAULT 0`,
      `locked_until TEXT`.
    - Place the block after the existing table creation statements so all tables are always
      present before any other code runs.
    - _Requirements: 2.1, 2.3_

  - [x] 1.2 Implement `next_account_number(conn)` helper in `storage.py`
    - Add `next_account_number(conn: sqlite3.Connection) -> str` that queries
      `SELECT MAX(CAST(account_number AS INTEGER)) FROM mock_accounts`, increments by 1,
      zero-pads to 6 digits, and raises `ValueError` if the result would exceed `999999`.
    - Must be called inside a transaction to prevent duplicate assignment.
    - _Requirements: 1.2, 1.3, 1.7_

  - [ ]* 1.3 Write property test for `next_account_number` format invariant
    - **Property 11: Account number format invariant**
    - **Validates: Requirements 1.1, 1.2**
    - In `tests/test_customer_pin_auth_properties.py`, use `st.integers(0, 999998)` as the
      seeded max value; assert the result matches `^[0-9]{6}$`.

  - [x] 1.4 Implement account-number migration in `_seed_mock_utility_data()`
    - Inside a single SQLite transaction, rename `"123456"→"000001"`, `"789012"→"000002"`,
      `"555666"→"000003"` in `mock_accounts`; update all FK references in `mock_bills` and
      `mock_payments`; detect and skip accounts that have already been migrated.
    - Roll back the entire transaction on any failure and re-raise so `init_db()` fails fast.
    - _Requirements: 1.4, 7.1, 7.2, 7.4_

- [x] 2. Checkpoint — schema and migration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement `backend/customer_auth.py` — `CustomerAuthService`
  - [x] 3.1 Create `backend/customer_auth.py` with `PinVerifyResult` dataclass and class skeleton
    - Define `PinVerifyResult(success, locked, locked_until, remaining_attempts)` dataclass.
    - Define `CustomerAuthService` class with `__init__` that accepts an optional `db_path`
      (defaults to the same path used by `storage.py`) so tests can inject an isolated DB.
    - Add `_validate_account_number` and `_validate_pin_format` private helpers that raise
      `ValueError` with the exact messages specified in the design.
    - Add module-level singleton `customer_auth_service = CustomerAuthService()`.
    - _Requirements: 2.1, 8.7_

  - [ ]* 3.2 Write property test for invalid account number rejection (Property 9)
    - **Property 9: Invalid account number format is rejected by all public Auth_Service methods**
    - **Validates: Requirements 8.7, 2.7**
    - Use `invalid_acct = st.text().filter(lambda s: not re.fullmatch(r"[0-9]{6}", s))`;
      assert `ValueError` is raised for `set_pin`, `verify_pin`, and `reset_pin`.

  - [x] 3.3 Implement `_hash_pin(pin, salt_hex) -> str`
    - Use `hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), 260_000)`;
      return the hex digest.
    - _Requirements: 2.2, 8.2_

  - [x] 3.4 Implement `set_pin(account_number, pin) -> None`
    - Call `_validate_account_number` and `_validate_pin_format` first.
    - Verify `account_number` exists in `mock_accounts`; raise `ValueError` if not.
    - Generate a 32-byte random salt with `os.urandom(32).hex()`.
    - Hash the PIN with `_hash_pin`.
    - `INSERT OR REPLACE INTO customer_auth` with `failed_attempts=0` and `locked_until=NULL`.
    - _Requirements: 2.2, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [ ]* 3.5 Write property test for `set_pin` upsert behaviour (Property 7)
    - **Property 7: set_pin is an upsert that resets lockout state**
    - **Validates: Requirements 2.2, 2.4, 2.8, 4.7**
    - Use `valid_account` and two different `valid_pin` values; call `set_pin` twice; assert
      only the second PIN verifies and `failed_attempts == 0`, `locked_until IS NULL`.

  - [ ]* 3.6 Write property test for invalid PIN format rejection (Property 8)
    - **Property 8: Invalid PIN format is rejected before hashing**
    - **Validates: Requirements 2.6, 8.3**
    - Use `invalid_pin = st.text().filter(lambda s: not re.fullmatch(r"[0-9]{4}", s))`;
      assert `ValueError` is raised and `customer_auth` is not modified.

  - [x] 3.7 Implement `verify_pin(account_number, candidate_pin) -> PinVerifyResult`
    - Call `_validate_account_number`.
    - Fetch the row from `customer_auth`; if absent, return
      `PinVerifyResult(success=False, locked=False, locked_until=None, remaining_attempts=3)`.
    - Check `locked_until`: if non-NULL and `datetime.utcnow() < locked_until`, return locked
      result without incrementing `failed_attempts`.
    - Hash `candidate_pin` with the stored salt; compare using `hmac.compare_digest`.
    - On success: `UPDATE failed_attempts=0, locked_until=NULL`; return success result.
    - On failure: increment `failed_attempts`; if it reaches 3, set
      `locked_until = utcnow + timedelta(minutes=15)` and return locked result; otherwise
      return failure result with `remaining_attempts = 3 - new_failed_attempts`.
    - _Requirements: 3.3, 3.5, 4.1, 4.2, 4.3, 4.5, 4.8, 8.1_

  - [ ]* 3.8 Write property test for successful verification resets counter (Property 5)
    - **Property 5: Successful PIN verification resets failed_attempts**
    - **Validates: Requirements 3.5, 4.5, 4.6**
    - Seed an account with `failed_attempts` in 1–2 and correct PIN; call `verify_pin` with
      correct PIN; assert `failed_attempts == 0` and `locked_until IS NULL`.

  - [ ]* 3.9 Write property test for failure increments counter / locked counter frozen (Property 6)
    - **Property 6: Failed PIN verification increments counter; locked account counter is frozen**
    - **Validates: Requirements 4.1, 4.3, 4.8**
    - Sub-case A: unlocked account with `failed_attempts` 0–2, wrong PIN → assert
      `failed_attempts == N + 1`.
    - Sub-case B: locked account, any PIN → assert `failed_attempts` unchanged.

  - [x] 3.10 Implement `reset_pin(account_number, new_pin) -> None`
    - Call `_validate_account_number` and `_validate_pin_format`.
    - Log a security event via `_log_security_event` before and after the operation
      (record outcome: success or failure reason).
    - Delegate to `set_pin` for the actual hash-and-store step.
    - _Requirements: 4.7, 6.6, 6.8_

  - [ ]* 3.11 Write property test for audit log always written (Property 14)
    - **Property 14: Admin reset audit log is always written**
    - **Validates: Requirements 6.8**
    - Call `reset_pin` with both valid and invalid inputs; assert an `audit_logs` row is
      inserted in every case.

- [x] 4. Checkpoint — `CustomerAuthService` complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Add PIN gate to `backend/agent.py` billing branch
  - [ ] 5.1 Add account-number validation and zero-padding to `run_agent()` billing branch
    - Import `re` if not already imported.
    - After resolving `acct` from context, zero-pad numeric strings shorter than 6 digits
      using `acct.zfill(6)`.
    - Reject inputs that do not match `r"\d{6}"` (non-numeric or >6 digits): track re-entry
      attempts in session; after 3 invalid attempts, end the billing flow.
    - _Requirements: 1.5, 1.6, 5.1_

  - [ ]* 5.2 Write property test for short account zero-padding (Property 12)
    - **Property 12: Short numeric account input is zero-padded by BillingAgent**
    - **Validates: Requirements 1.5**
    - Use `st.integers(1, 99999)` converted to strings; assert the padded value matches
      `^[0-9]{6}$` and equals `str(original).zfill(6)`.

  - [~] 5.3 Add PIN gate logic to `run_agent()` billing branch
    - Import `customer_auth_service` from `backend.customer_auth`.
    - After account-number validation, check `entities.get("pin_verified")`.
    - If not verified: extract a 4-digit PIN from the message with `re.fullmatch(r"\d{4}", ...)`;
      if absent, return the PIN prompt (must not include the account number in the reply).
    - Call `customer_auth_service.verify_pin(acct, candidate)`; handle locked, failure, and
      success cases as specified in the design.
    - On success: set `entities["pin_verified"] = True` and persist to session.
    - _Requirements: 3.2, 3.3, 3.4, 3.6, 3.7, 4.4, 5.2, 5.3, 5.4, 5.5, 5.8, 8.4_

  - [ ]* 5.4 Write property test for unverified session prompts for PIN (Property 2)
    - **Property 2: Unverified session → billing agent prompts for PIN**
    - **Validates: Requirements 3.2, 3.7, 5.2**
    - Generate random contexts with a valid `account_number` but no `pin_verified`; assert
      the reply asks for PIN and contains no billing data.

  - [ ]* 5.5 Write property test for no account number prompts for account (Property 1)
    - **Property 1: No account number → billing agent prompts for account number**
    - **Validates: Requirements 3.1, 5.1**
    - Generate random contexts without `account_number`; assert the reply asks for account
      number and contains no billing data.

  - [ ]* 5.6 Write property test for verified session returns billing data (Property 4)
    - **Property 4: Verified session returns billing data directly**
    - **Validates: Requirements 3.4, 5.3, 5.6**
    - Generate contexts with `pin_verified=True` and a valid seeded account; assert the reply
      contains billing data and does not prompt for PIN.

  - [ ]* 5.7 Write property test for PIN prompt does not reveal account number (Property 13)
    - **Property 13: PIN prompt does not reveal account number**
    - **Validates: Requirements 8.4**
    - For any valid `account_number` in context (not yet verified), assert the PIN prompt
      reply does not contain the `account_number` string.

  - [ ]* 5.8 Write property test for context reset clears PIN verification (Property 3)
    - **Property 3: Context reset clears PIN verification**
    - **Validates: Requirements 3.8, 5.7**
    - Generate contexts with `pin_verified=True`; call `context_manager.reset_context()`;
      assert the resulting context does not have `pin_verified == True`.

- [~] 6. Checkpoint — PIN gate wired into billing flow
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Add admin PIN reset endpoint to `main.py`
  - [~] 7.1 Add `ResetPinRequest` Pydantic model and `POST /admin/accounts/{account_number}/reset-pin` endpoint
    - Define `ResetPinRequest(BaseModel)` with `new_pin: str`.
    - Implement the endpoint: call `_require_admin(authorization)`, then
      `customer_auth_service.reset_pin(account_number, body.new_pin)`.
    - Map `ValueError` with "not found" → HTTP 404; other `ValueError` → HTTP 422;
      `sqlite3.Error` → HTTP 500.
    - Return `{"status": "ok", "account_number": account_number}` on success.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 8.5_

  - [ ]* 7.2 Write property test for invalid token rejection (Property 10)
    - **Property 10: Admin reset endpoint rejects missing or invalid tokens**
    - **Validates: Requirements 6.2, 6.3, 8.6**
    - Use random invalid token strings (missing, malformed, wrong value); assert HTTP 401 or
      403 is returned and `customer_auth` is not modified.

- [ ] 8. Seed demo PINs in `_seed_mock_utility_data()`
  - [~] 8.1 Call `customer_auth_service.set_pin()` for demo accounts after migration
    - After the account-number migration, call `set_pin("000001", "1234")`,
      `set_pin("000002", "5678")`, `set_pin("000003", "9012")` only if no PIN row already
      exists for each account (use `SELECT 1 FROM customer_auth WHERE account_number=?`).
    - Add a comment adjacent to the calls documenting the demo PINs:
      `# Demo PINs: 000001→"1234", 000002→"5678", 000003→"9012"`.
    - _Requirements: 7.3, 7.4, 7.5_

- [ ] 9. Write example-based unit tests in `tests/test_customer_pin_auth.py`
  - [~] 9.1 Write unit tests for `CustomerAuthService` core behaviour
    - `test_set_pin_stores_hash_not_plaintext` — stored `pin_hash` ≠ plaintext PIN.
    - `test_verify_pin_correct` — correct PIN → `success=True`.
    - `test_verify_pin_wrong` — wrong PIN → `success=False`.
    - `test_lockout_after_3_failures` — 3rd failure sets `locked_until` ≈ now+15min.
    - `test_locked_account_rejects_correct_pin` — correct PIN rejected while locked.
    - `test_lockout_expires` — after `locked_until` passes, correct PIN succeeds.
    - `test_admin_reset_unlocks_account` — `reset_pin()` on locked account clears lock.
    - _Requirements: 2.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.5, 4.7, 8.1_

  - [~] 9.2 Write unit tests for storage migration and demo seeding
    - `test_migration_account_numbers` — `"123456"→"000001"` etc. with FK updates verified.
    - `test_demo_pin_seeding` — demo PINs `"1234"`, `"5678"`, `"9012"` work after `init_db()`.
    - `test_demo_pin_not_overwritten` — re-running `init_db()` does not overwrite changed PINs.
    - `test_account_number_exhaustion` — `next_account_number()` raises `ValueError` at 999999.
    - _Requirements: 1.4, 1.7, 7.1, 7.2, 7.3, 7.4_

  - [~] 9.3 Write unit tests for the admin reset endpoint
    - `test_admin_reset_endpoint_401` — missing token → HTTP 401.
    - `test_admin_reset_endpoint_404` — unknown account → HTTP 404.
    - `test_admin_reset_endpoint_422` — invalid PIN format → HTTP 422.
    - `test_admin_reset_endpoint_200` — valid request → HTTP 200 + `{"status": "ok", ...}`.
    - `test_audit_log_on_reset_success` — audit log entry created on success.
    - `test_audit_log_on_reset_failure` — audit log entry created on validation failure.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [~] 9.4 Write unit tests for `BillingAgent` PIN flow edge cases
    - `test_pin_prompt_excludes_account_number` — PIN prompt reply does not contain account number.
    - _Requirements: 8.4_

- [~] 10. Final checkpoint — full test suite
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation at each phase boundary.
- Property tests use Hypothesis with `@settings(max_examples=100)` and the tag format
  `# Feature: customer-pin-auth, Property N: <property text>`.
- Unit tests use isolated SQLite databases (inject `db_path` or use `tmp_path` fixtures) to
  avoid polluting the development database.
- Demo PINs are documented in `storage.py` adjacent to the seed calls:
  `000001→"1234"`, `000002→"5678"`, `000003→"9012"`.
- The `customer_auth` table is never exposed through any non-`/admin/` endpoint (Requirement 8.5).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4"] },
    { "id": 3, "tasks": ["3.5", "3.6", "3.7"] },
    { "id": 4, "tasks": ["3.8", "3.9", "3.10"] },
    { "id": 5, "tasks": ["3.11", "5.1"] },
    { "id": 6, "tasks": ["5.2", "5.3"] },
    { "id": 7, "tasks": ["5.4", "5.5", "5.6", "5.7", "5.8", "7.1"] },
    { "id": 8, "tasks": ["7.2", "8.1"] },
    { "id": 9, "tasks": ["9.1", "9.2", "9.3", "9.4"] }
  ]
}
```
