"""Authentication providers module."""

from .base import AuthProviderInterface
from .local import LocalAuthProvider

__all__ = ["AuthProviderInterface", "LocalAuthProvider"]
