from dataclasses import dataclass
from typing import Generic

import bcrypt

from app.common_lib.domain.model import IdModel, ID
from app.common_lib.errors import AppError
from app.common_lib.executor import cpu_bound

MAX_ENCODED_PASSWORD_LEN = 72  # bcrypt limit


class UserRegisterEvent:
    pass


class EmailIsNotVerified(AppError):
    pass


class WrongPassword(AppError):
    pass


class EmailIsAlreadyVerified(AppError):
    pass


@dataclass
class HashedPassword:
    value: bytes


@cpu_bound
def hash_password(password: bytes) -> HashedPassword:
    return HashedPassword(value=bcrypt.hashpw(password, bcrypt.gensalt()))


def check_password(password: bytes, hashed: bytes):
    if not bcrypt.checkpw(password, hashed):
        raise WrongPassword()


class UserAuth(IdModel, Generic[ID]):
    email: str
    hashed_password: bytes
    is_admin: bool = False
    is_email_verified: bool = False

    @classmethod
    def create(cls, email: str, hashed_password: HashedPassword) -> 'UserAuth':
        user_auth = cls(
            email=email,
            hashed_password=hashed_password.value
        )

        return user_auth

    def check_is_email_not_verified(self):
        if self.is_email_verified:
            raise EmailIsAlreadyVerified()

    def verify_email(self):
        self.is_email_verified = True

    def check_password(self, password: bytes):
        check_password(password, self.hashed_password)

    def check_can_user_login(self, password: bytes):
        self.check_password(password)

        if not self.is_email_verified:
            raise EmailIsNotVerified()
