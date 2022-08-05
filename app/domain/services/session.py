from dataclasses import dataclass
from typing import Tuple

from app.common_lib.errors import AppError
from app.domain.models.session import Session, ReusingOfRefreshToken
from app.domain.repos.session import ISessionRepo
from app.domain.models.tokens import AccessToken, RefreshToken, \
    RefreshTokenWithoutExpireValidation
from app.domain.models.user import UserAuth
from app.domain.repos.user import IUserAuthRepo


class UserWithEmailDoesntExists(AppError):
    pass


@dataclass
class LoginDTO:
    email: str
    password: bytes


class SessionService:
    def __init__(self, user_repo: IUserAuthRepo, session_repo: ISessionRepo):
        self._user_repo = user_repo
        self._session_repo = session_repo

    async def _find_user_by_email(self, email: str) -> UserAuth:
        user = await self._user_repo.find_by_email(email)
        if not user:
            raise UserWithEmailDoesntExists()

        return user

    async def login(self, dto: LoginDTO) -> Tuple[AccessToken, RefreshToken]:
        user = await self._find_user_by_email(dto.email)
        user.check_can_user_login(dto.password)

        access_token, refresh_token = AccessToken.create(user), RefreshToken.create(user)

        session = Session.create(user, refresh_token)
        await self._session_repo.insert(session)

        return access_token, refresh_token

    async def _invalidate_session_family(self, session: Session):
        await self._session_repo.invalidate_session_family(session)

    async def refresh(self, refresh_token: RefreshTokenWithoutExpireValidation) -> Tuple[AccessToken, RefreshToken]:
        session: Session = await self._session_repo.find_session_by_token(token=refresh_token.get_token())

        try:
            session.refresh()
        except ReusingOfRefreshToken as ex:
            await self._invalidate_session_family(session)
            raise ex

        user: UserAuth = await self._user_repo.find_by_id(session.user_id)

        new_access_token, new_refresh_token = AccessToken.create(user=user), RefreshToken.create(user=user)
        new_session = Session.create_from_refreshed(refreshed_session=session, refresh_token=new_refresh_token)

        await self._session_repo.update(session)
        await self._session_repo.insert(new_session)

        return new_access_token, new_refresh_token

    async def logout(self, access_token: AccessToken, session_id: str):
        session = await self._session_repo.find_session_by_id(_id=session_id, user_id=access_token.sub)
        session.logout()
        await self._session_repo.update(session)
