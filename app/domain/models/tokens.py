from abc import ABC
from datetime import datetime, timedelta
from enum import Enum
from typing import TypeVar, Type, Any, Optional

from bson import ObjectId
from jose import jwt, jws
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError, JWSError
from pydantic import ValidationError, Field, PrivateAttr
from pydantic.main import BaseModel

from app.common_lib.errors import AppError
from app.domain.models.user import UserAuth

ALGORITHM = 'HS256'
SECRET = '123'

REGISTRATION_TOKEN_EXPIRE_MINUTES = 10
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_MINUTES = 24 * 60 * 60


class TokenVerificationFailed(AppError):
    pass


class WrongTokenFormat(AppError):
    pass


TokenType = TypeVar('TokenType', bound='Token')


class TokenKind(Enum):
    REGISTRATION = 'REGISTRATION'
    ACCESS = 'ACCESS'
    REFRESH = 'REFRESH'


class Token(BaseModel, ABC):
    jti: str = Field(default_factory=lambda: str(ObjectId()))
    _token_cache: str = PrivateAttr(default=None)

    class Config:
        allow_mutation = False

    def _set_token_cache(self, token: str):
        self._token_cache = token

    def _generate_token(self) -> str:
        return jwt.encode(claims=self.dict(), key=SECRET, algorithm=ALGORITHM)

    def __init__(self, _token_cache: Optional[str] = None, **data: Any):
        super().__init__(**data)

        if _token_cache:
            self._set_token_cache(_token_cache)
        else:
            self._set_token_cache(self._generate_token())

    def get_token(self) -> str:
        return self._token_cache

    @classmethod
    def _decode_and_validate(cls: Type[TokenType], token: str, validation_options: dict = None) -> TokenType:
        try:
            claims = jwt.decode(token, SECRET, algorithms=ALGORITHM, options=validation_options)
        except (JWTError, JWTClaimsError, ExpiredSignatureError) as ex:
            raise TokenVerificationFailed(ex) from ex

        try:
            token_obj: TokenType = cls(_token_cache=token, **claims)
        except ValidationError as ex:
            raise WrongTokenFormat(ex.json())

        return token_obj

    @classmethod
    def decode_and_validate(cls: Type[TokenType], token: str) -> TokenType:
        return cls._decode_and_validate(token=token, validation_options=None)


class RegistrationToken(Token):
    token_kind: str = Field(default=TokenKind.REGISTRATION.value, const=True)
    sub: str
    exp: datetime

    @classmethod
    def create(cls, user: UserAuth) -> 'RegistrationToken':
        return cls(
            sub=str(user.id),
            exp=datetime.now() + timedelta(minutes=REGISTRATION_TOKEN_EXPIRE_MINUTES),
        )


class AccessTokenData(BaseModel):
    ...


class AccessToken(Token):
    token_kind: str = Field(default=TokenKind.ACCESS.value, const=True)
    sub: str
    exp: datetime
    data: AccessTokenData

    @classmethod
    def create(cls, user: UserAuth) -> 'AccessToken':
        data = AccessTokenData()

        return cls(
            sub=str(user.id),
            exp=datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            data=data
        )


class RefreshToken(Token):
    token_kind: str = Field(default=TokenKind.REFRESH.value, const=True)
    sub: str
    exp: datetime

    @classmethod
    def create(cls, user: UserAuth) -> 'RefreshToken':
        return cls(
            sub=str(user.id),
            exp=datetime.now() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
        )


class RefreshTokenWithoutExpireValidation(RefreshToken):
    @classmethod
    def decode_and_validate(cls: Type[TokenType], token: str) -> TokenType:
        return cls._decode_and_validate(token=token, validation_options={'verify_exp': False})
