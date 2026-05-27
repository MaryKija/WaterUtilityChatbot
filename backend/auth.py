"""backend/auth.py

Authentication and authorization system for admin access.

This module provides:
- Token-based authentication for admin users
- Role-based access control (RBAC)
- PII protection for public endpoints
- Audit logging for admin actions
"""

import hashlib
import os
import secrets
import time
import re
import base64
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from .logger import logger
from .storage import _connect, ADMIN_RESOLUTION_TABLE

def base64url_encode(data: bytes) -> str:
    """Base64URL encode according to RFC 7515 (no padding, url-safe)."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(s: str) -> bytes:
    """Base64URL decode according to RFC 7515 (restores padding if missing)."""
    rem = len(s) % 4
    if rem > 0:
        s += '=' * (4 - rem)
    return base64.urlsafe_b64decode(s.encode('utf-8'))



class UserRole(Enum):
    """User roles with different permission levels."""
    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(Enum):
    """System permissions for role-based access control."""
    # Customer permissions
    VIEW_OWN_COMPLAINTS = "view_own_complaints"
    SUBMIT_COMPLAINTS = "submit_complaints"
    VIEW_OWN_BILLING = "view_own_billing"
    
    # Admin permissions
    VIEW_ALL_COMPLAINTS = "view_all_complaints"
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_RESOLUTIONS = "manage_resolutions"
    VIEW_ANALYTICS = "view_analytics"
    
    # Super admin permissions
    MANAGE_ADMINS = "manage_admins"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIG = "system_config"


@dataclass
class AdminUser:
    """Admin user account with role and permissions."""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[Permission]
    created_at: str
    last_login: Optional[str] = None
    active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None


@dataclass
class AuthToken:
    """Authentication token with metadata."""
    token_id: str
    user_id: str
    token_hash: str
    expires_at: str
    created_at: str
    last_used: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    active: bool = True


@dataclass
class AuditLog:
    """Audit log entry for security tracking."""
    log_id: str
    user_id: str
    action: str
    resource: str
    timestamp: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    details: Optional[Dict[str, Any]] = None


class AuthenticationError(Exception):
    """Authentication failed error."""
    pass


class AuthorizationError(Exception):
    """Authorization failed error."""
    pass


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        # Default admin users (in production, these would be in database)
        self._default_admins = {
            "admin": {
                "user_id": "admin_001",
                "username": "admin",
                "email": "admin@waterutility.ai",
                "role": UserRole.ADMIN,
                "permissions": [
                    Permission.VIEW_ALL_COMPLAINTS,
                    Permission.VIEW_DASHBOARD,
                    Permission.MANAGE_RESOLUTIONS,
                    Permission.VIEW_ANALYTICS
                ],
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "superadmin": {
                "user_id": "admin_000", 
                "username": "superadmin",
                "email": "superadmin@waterutility.ai",
                "role": UserRole.SUPER_ADMIN,
                "permissions": list(Permission),  # All permissions
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Token storage (in production, these would be in database)
        self._active_tokens: Dict[str, AuthToken] = {}
        
        # Initialize database tables for audit logging
        self._init_audit_tables()
    
    def _init_audit_tables(self):
        """Initialize audit logging and token persistence tables."""
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    details TEXT
                )
                """
            )
            # Persist session tokens so they survive server restarts
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_secret TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            # Clean up expired tokens on startup
            conn.execute(
                "DELETE FROM auth_tokens WHERE expires_at < ?",
                (datetime.now(timezone.utc).isoformat(),)
            )
    
    def authenticate_user(self, username: str, password: str) -> AdminUser:
        """Authenticate user with username and password.

        Passwords are read from environment variables so they are never
        hardcoded in source.  Variable lookup order:
          1. ADMIN_PASSWORD_<USERNAME_UPPER>  (e.g. ADMIN_PASSWORD_ADMIN)
          2. ADMIN_DEFAULT_PASSWORD           (fallback for both accounts)

        If neither variable is set the login is rejected — this prevents
        accidental access when the env file has not been configured.
        """
        import hmac as _hmac

        if username not in self._default_admins:
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "user_not_found",
            })
            raise AuthenticationError("Invalid credentials")

        # Resolve expected password from environment — never from source code
        env_key = f"ADMIN_PASSWORD_{username.upper()}"
        expected_pw = os.getenv(env_key) or os.getenv("ADMIN_DEFAULT_PASSWORD", "")

        if not expected_pw:
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "password_not_configured",
            })
            raise AuthenticationError("Invalid credentials")

        # Constant-time comparison prevents timing-based enumeration
        if not _hmac.compare_digest(password, expected_pw):
            self._log_security_event("failed_login", "auth", {
                "username": username,
                "reason": "invalid_password",
            })
            raise AuthenticationError("Invalid credentials")

        user_data = self._default_admins[username].copy()
        user_data["last_login"] = datetime.now(timezone.utc).isoformat()

        self._log_security_event("successful_login", "auth", {
            "username": username,
            "user_id": user_data["user_id"],
        })

        role = user_data["role"]
        permissions = user_data["permissions"]
        if not isinstance(role, UserRole):
            raise TypeError("role must be a UserRole")
        if not isinstance(permissions, list):
            raise TypeError("permissions must be a list")

        user_id_val = user_data["user_id"]
        username_val = user_data["username"]
        email_val = user_data["email"]
        created_at_val = user_data["created_at"]

        if not isinstance(user_id_val, str):
            raise TypeError("user_id must be a string")
        if not isinstance(username_val, str):
            raise TypeError("username must be a string")
        if not isinstance(email_val, str):
            raise TypeError("email must be a string")
        if not isinstance(created_at_val, str):
            raise TypeError("created_at must be a string")

        last_login_val = user_data.get("last_login")
        last_login = last_login_val if isinstance(last_login_val, str) else None

        failed_attempts_val = user_data.get("failed_login_attempts", 0)
        failed_login_attempts = int(failed_attempts_val) if isinstance(failed_attempts_val, (int, str)) else 0

        locked_until_val = user_data.get("locked_until")
        locked_until = locked_until_val if isinstance(locked_until_val, str) else None

        return AdminUser(
            user_id=user_id_val,
            username=username_val,
            email=email_val,
            role=role,
            permissions=permissions,
            created_at=created_at_val,
            last_login=last_login,
            active=bool(user_data.get("active", True)),
            failed_login_attempts=failed_login_attempts,
            locked_until=locked_until,
        )
    
    def generate_token(self, user: AdminUser, expires_hours: int = 24) -> AuthToken:
        """Generate a secure stateless/stateful hybrid JWT and persist its JTI to the database."""
        jti = f"JTI_{secrets.token_hex(16)}"
        created_dt = datetime.now(timezone.utc)
        expires_dt = created_dt + timedelta(hours=expires_hours)

        # Standard JWT Header & Payload
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "jti": jti,
            "sub": user.user_id,
            "role": user.role.value,
            "permissions": [p.value for p in user.permissions],
            "iat": int(created_dt.timestamp()),
            "exp": int(expires_dt.timestamp())
        }

        # Serialize and encode payload
        header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
        payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))

        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        secret_key = os.getenv("JWT_SECRET_KEY") or os.getenv("ADMIN_TOKEN") or "fallback_super_secret_key_123!"

        import hmac
        signature = hmac.new(secret_key.encode('utf-8'), signing_input, hashlib.sha256).digest()
        signature_b64 = base64url_encode(signature)

        jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"

        expires_at_iso = expires_dt.isoformat()
        created_at_iso = created_dt.isoformat()

        # Persist to database so the JTI survives server restarts and can be revoked
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_tokens (token_id, user_id, token_secret, expires_at, created_at, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (jti, user.user_id, jwt_token, expires_at_iso, created_at_iso),
            )

        self._log_security_event("token_generated", "auth", {
            "user_id": user.user_id,
            "jti": jti,
            "expires_at": expires_at_iso,
        })

        return AuthToken(
            token_id=jti,
            user_id=user.user_id,
            token_hash=jwt_token,   # Return the full JWT to the caller
            expires_at=expires_at_iso,
            created_at=created_at_iso,
            permissions=user.permissions,
            active=True,
        )

    def verify_token(self, token: str) -> Optional[AdminUser]:
        """Verify the hybrid JWT statelessly (cryptography) and statefully (revocation check)."""
        if not token:
            return None

        # 1. Parse JWT structure
        parts = token.split('.')
        if len(parts) != 3:
            # Fallback to checking the token directly in the database (backward compatibility for non-JWT tokens)
            now = datetime.now(timezone.utc).isoformat()
            with _connect() as conn:
                row = conn.execute(
                    """
                    SELECT token_id, user_id, expires_at, active
                    FROM auth_tokens
                    WHERE token_secret = ? AND active = 1 AND expires_at > ?
                    """,
                    (token, now),
                ).fetchone()
            if not row:
                self._log_security_event("invalid_token", "auth", {
                    "reason": "malformed_jwt_structure_and_not_in_db",
                })
                return None
            token_id, user_id, expires_at, active = row
            # Update last_used timestamp
            with _connect() as conn:
                conn.execute(
                    "UPDATE auth_tokens SET last_used = ? WHERE token_id = ?",
                    (now, token_id),
                )
            # Resolve user
            for admin_data in self._default_admins.values():
                if admin_data["user_id"] == user_id:
                    return AdminUser(**admin_data)
            return None

        header_b64, payload_b64, signature_b64 = parts

        # 2. Cryptographic signature check
        try:
            signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
            secret_key = os.getenv("JWT_SECRET_KEY") or os.getenv("ADMIN_TOKEN") or "fallback_super_secret_key_123!"
            import hmac
            expected_sig = hmac.new(secret_key.encode('utf-8'), signing_input, hashlib.sha256).digest()
            expected_sig_b64 = base64url_encode(expected_sig)

            # Constant-time comparison
            import hmac as _hmac
            if not _hmac.compare_digest(signature_b64.encode('utf-8'), expected_sig_b64.encode('utf-8')):
                self._log_security_event("invalid_token", "auth", {
                    "reason": "signature_mismatch",
                })
                return None

            # Decode payload
            payload_json = base64url_decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
        except Exception as e:
            self._log_security_event("invalid_token", "auth", {
                "reason": f"decode_error: {str(e)}",
            })
            return None

        # 3. Check expiration statelessly
        exp = payload.get("exp")
        jti = payload.get("jti")
        user_id = payload.get("sub")

        if not exp or not jti or not user_id:
            self._log_security_event("invalid_token", "auth", {
                "reason": "missing_required_claims",
            })
            return None

        now_ts = int(time.time())
        if now_ts > exp:
            self._log_security_event("invalid_token", "auth", {
                "reason": "token_expired_stateless",
                "jti": jti,
            })
            return None

        # 4. Stateful revocation / database check
        now_iso = datetime.now(timezone.utc).isoformat()
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT token_id, active, expires_at
                FROM auth_tokens
                WHERE token_id = ? AND active = 1 AND expires_at > ?
                """,
                (jti, now_iso),
            ).fetchone()

        if not row:
            self._log_security_event("invalid_token", "auth", {
                "reason": "revoked_or_expired_stateful",
                "jti": jti,
            })
            return None

        # 5. Update last_used timestamp statefully
        with _connect() as conn:
            conn.execute(
                "UPDATE auth_tokens SET last_used = ? WHERE token_id = ?",
                (now_iso, jti),
            )

        # 6. Resolve user from registry
        user_data = None
        for admin_data in self._default_admins.values():
            if admin_data["user_id"] == user_id:
                user_data = admin_data.copy()
                break

        if not user_data:
            self._log_security_event("invalid_token", "auth", {
                "reason": "user_not_found_in_registry",
                "user_id": user_id,
            })
            return None

        role = user_data["role"]
        permissions = user_data["permissions"]
        if not isinstance(role, UserRole):
            raise TypeError("role must be a UserRole")
        if not isinstance(permissions, list):
            raise TypeError("permissions must be a list")

        user_id_val = user_data["user_id"]
        username_val = user_data["username"]
        email_val = user_data["email"]
        created_at_val = user_data["created_at"]

        if not isinstance(user_id_val, str):
            raise TypeError("user_id must be a string")
        if not isinstance(username_val, str):
            raise TypeError("username must be a string")
        if not isinstance(email_val, str):
            raise TypeError("email must be a string")
        if not isinstance(created_at_val, str):
            raise TypeError("created_at must be a string")

        last_login_val = user_data.get("last_login")
        last_login = last_login_val if isinstance(last_login_val, str) else None

        failed_attempts_val = user_data.get("failed_login_attempts", 0)
        failed_login_attempts = int(failed_attempts_val) if isinstance(failed_attempts_val, (int, str)) else 0

        locked_until_val = user_data.get("locked_until")
        locked_until = locked_until_val if isinstance(locked_until_val, str) else None

        return AdminUser(
            user_id=user_id_val,
            username=username_val,
            email=email_val,
            role=role,
            permissions=permissions,
            created_at=created_at_val,
            last_login=last_login,
            active=bool(user_data.get("active", True)),
            failed_login_attempts=failed_login_attempts,
            locked_until=locked_until,
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke the JWT statefully by flagging its JTI as inactive in the database."""
        if not token:
            return False

        # Try to parse and extract JTI
        jti = None
        parts = token.split('.')
        if len(parts) == 3:
            try:
                payload_b64 = parts[1]
                payload_json = base64url_decode(payload_b64).decode('utf-8')
                payload = json.loads(payload_json)
                jti = payload.get("jti")
            except Exception:
                pass

        # Revoke by JTI or full token string in the DB (covers JWT and legacy cases)
        with _connect() as conn:
            if jti:
                cur = conn.execute(
                    "UPDATE auth_tokens SET active = 0 WHERE token_id = ? OR token_secret = ?",
                    (jti, token),
                )
            else:
                cur = conn.execute(
                    "UPDATE auth_tokens SET active = 0 WHERE token_secret = ?",
                    (token,),
                )
            revoked = cur.rowcount > 0

        if revoked:
            self._log_security_event("token_revoked", "auth", {
                "jti": jti,
                "token_prefix": token[:12] + "..."
            })

        return revoked
    
    def check_permission(self, user: AdminUser, permission: Permission) -> bool:
        """Check if user has required permission."""
        return permission in user.permissions
    
    def require_permission(self, user: AdminUser, permission: Permission):
        """Require user to have specific permission or raise error."""
        if not self.check_permission(user, permission):
            self._log_security_event("permission_denied", "auth", {
                "user_id": user.user_id,
                "permission": permission.value,
                "user_role": user.role.value
            })
            raise AuthorizationError(f"Permission required: {permission.value}")
    
    def _log_security_event(self, action: str, resource: str, details: Dict[str, Any]):
        """Log security event for audit trail."""
        log_id = f"AUD_{secrets.token_hex(12)}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        audit_log = AuditLog(
            log_id=log_id,
            user_id=details.get("user_id", "system"),
            action=action,
            resource=resource,
            timestamp=timestamp,
            details=details
        )
        
        # Store in database
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (log_id, user_id, action, resource, timestamp, ip_address, user_agent, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_log.log_id,
                    audit_log.user_id,
                    audit_log.action,
                    audit_log.resource,
                    audit_log.timestamp,
                    audit_log.ip_address,
                    audit_log.user_agent,
                    audit_log.success,
                    str(details) if audit_log.details else None
                )
            )
        
        # Also log to application logger
        logger.warning(
            f"security.{action}",
            extra={"extra_data": details}
        )

    def log_admin_action(self, admin_id: str, action: str, resource: str, before_state: Any, after_state: Any, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Log an administrative action with detailed before/after states."""
        log_id = f"AUD_{secrets.token_hex(12)}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        details = {
            "before": before_state,
            "after": after_state
        }
        
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (log_id, user_id, action, resource, timestamp, ip_address, user_agent, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    admin_id,
                    action,
                    resource,
                    timestamp,
                    ip_address,
                    user_agent,
                    True,
                    json.dumps(details)
                )
            )
        
        logger.info(
            f"audit.{action}",
            extra={"extra_data": {"admin_id": admin_id, "resource": resource, "details": details}}
        )


class PIIProtection:
    """PII protection for public endpoints."""
    
    @staticmethod
    def redact_complaint_data(complaint_data: Dict[str, Any], user_role: UserRole) -> Dict[str, Any]:
        """Redact PII from complaint data based on user role."""
        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            # Admins can see all data
            return complaint_data
        
        # For customers, redact sensitive information
        redacted = complaint_data.copy()
        
        # Redact full name, show only first initial
        if "name" in redacted:
            name = redacted["name"]
            if isinstance(name, str) and len(name) > 1:
                redacted["name"] = name[0] + "***"
        
        # Redact specific address details
        if "area" in redacted:
            area = redacted["area"]
            if isinstance(area, str) and len(area) > 10:
                redacted["area"] = area[:10] + "***"
        
        # Remove phone numbers if present
        if "phone" in redacted:
            redacted["phone"] = "***-***-****"
        
        # Remove email addresses if present
        if "email" in redacted:
            email = redacted["email"]
            if isinstance(email, str) and "@" in email:
                local, domain = email.split("@", 1)
                redacted["email"] = local[0] + "***@" + domain
        
        return redacted
    
    @staticmethod
    def redact_conversation_history(history: List[Dict[str, Any]], user_role: UserRole) -> List[Dict[str, Any]]:
        """Redact PII from conversation history."""
        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return history
        
        redacted_history = []
        
        for entry in history:
            redacted_entry = entry.copy()
            
            # Redact PII from user messages
            if entry.get("role") == "user":
                text = entry.get("text", "")
                # Simple PII redaction patterns
                text = re.sub(r'\b\d{10,}\b', '***-***-****', text)  # Phone numbers
                text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)  # Emails
                text = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '*** ***', text)  # Names
                
                redacted_entry["text"] = text
            
            redacted_history.append(redacted_entry)
        
        return redacted_history


# Global auth service instance
auth_service = AuthService()


# Decorators for endpoint protection
def require_auth(permission: Optional[Permission] = None):
    """Decorator to require authentication and optional permission."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be used with FastAPI dependencies
            # For now, return the function as-is
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorator to require admin role."""
    return require_auth(Permission.VIEW_DASHBOARD)
