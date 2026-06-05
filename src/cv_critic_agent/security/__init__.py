"""Security primitives.

Every module here is independent and pure: no environment reads, no global
state. Callers pass secrets explicitly so rotation and testing stay easy.
"""
from cv_critic_agent.security.crypto import sign_token, verify_token

__all__ = ["sign_token", "verify_token"]
