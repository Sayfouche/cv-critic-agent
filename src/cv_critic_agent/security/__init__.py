"""Security primitives.

Every module here is independent and pure: no environment reads, no global
state. Callers pass secrets explicitly so rotation and testing stay easy.
"""
from cv_critic_agent.security.crypto import sign_token, verify_token
from cv_critic_agent.security.logging_filter import (
    EmailMaskingFilter,
    install_email_masking,
)
from cv_critic_agent.security.pii import decrypt_pii, encrypt_pii
from cv_critic_agent.security.security_middleware import (
    CSPConfig,
    SecurityHeadersMiddleware,
    make_limiter,
    verify_turnstile,
)

__all__ = [
    "CSPConfig",
    "EmailMaskingFilter",
    "SecurityHeadersMiddleware",
    "decrypt_pii",
    "encrypt_pii",
    "install_email_masking",
    "make_limiter",
    "sign_token",
    "verify_token",
    "verify_turnstile",
]
