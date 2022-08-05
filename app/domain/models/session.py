import uuid
from datetime import datetime
from enum import Enum
from typing import Generic

from pydantic import Field

from app.common_lib.domain.model import IdModel, ID
from app.common_lib.errors import AppError
from app.domain.models.tokens import RefreshToken
from app.domain.models.user import UserAuth


class SessionIsNotActive(AppError):
    pass


class ReusingOfRefreshToken(AppError):
    pass


class SessionStatus(Enum):
    ACTIVE = 'ACTIVE'
    LOGOUT = 'LOGOUT'
    REFRESHED = 'REFRESHED'
    COMPROMISED = 'COMPROMISED'


class Session(IdModel, Generic[ID]):
    user_id: ID
    family_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    refresh_token: str
    expiration_time: datetime
    status: SessionStatus

    @classmethod
    def create(cls, user: UserAuth, refresh_token: RefreshToken) -> 'Session':
        session = cls(
            user_id=user.id,
            refresh_token=refresh_token.get_token(),
            expiration_time=refresh_token.exp,
            status=SessionStatus.ACTIVE
        )

        return session

    @property
    def _is_expired(self) -> bool:
        if self.expiration_time <= datetime.now():
            return True
        return False

    def _check_is_active(self):
        if self.status is not SessionStatus.ACTIVE or self._is_expired:
            raise SessionIsNotActive()

    def logout(self):
        self._check_is_active()

        self.status = SessionStatus.LOGOUT

    def refresh(self):
        if self.status is SessionStatus.REFRESHED:
            raise ReusingOfRefreshToken()

        self._check_is_active()

        self.status = SessionStatus.REFRESHED

    @classmethod
    def create_from_refreshed(cls, refreshed_session: 'Session', refresh_token: RefreshToken) -> 'Session':
        assert refreshed_session.status is SessionStatus.REFRESHED

        new_session = cls(
            user_id=refreshed_session.user_id,
            family_id=refreshed_session.family_id,
            refresh_token=refresh_token.get_token(),
            expiration_time=refresh_token.exp,
            status=SessionStatus.ACTIVE
        )

        return new_session
