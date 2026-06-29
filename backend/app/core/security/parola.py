"""Parola özetleme — argon2id (plan kararı).

``argon2-cffi`` varsayılan olarak argon2id kullanır. Özet, yeniden özetleme gerekip
gerekmediğini (parametre güncellemesi) ``yeniden_ozetle_gerekli`` ile kontrol eder.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def parola_ozetle(parola: str) -> str:
    """Düz parolayı argon2id ile özetler."""
    return _hasher.hash(parola)


def parola_dogrula(ozet: str, parola: str) -> bool:
    """Özet ile parolayı karşılaştırır; eşleşmezse ``False``."""
    try:
        return _hasher.verify(ozet, parola)
    except (VerifyMismatchError, InvalidHashError):
        return False


def yeniden_ozetle_gerekli(ozet: str) -> bool:
    """Özet, güncel argon2 parametrelerine göre yeniden hesaplanmalı mı?"""
    return _hasher.check_needs_rehash(ozet)
