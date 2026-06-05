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

__all__ = [
    "EmailMaskingFilter",
    "decrypt_pii",
    "encrypt_pii",
    "install_email_masking",
    "sign_token",
    "verify_token",
]
