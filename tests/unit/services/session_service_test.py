import datetime
import time
from typing import Tuple

import pytest
import pytest_asyncio
from testfixtures import Replace, test_datetime

from app.domain.models.session import ReusingOfRefreshToken, SessionStatus, SessionIsNotActive
from app.domain.models.tokens import AccessToken, RefreshToken, RefreshTokenWithoutExpireValidation, \
    REFRESH_TOKEN_EXPIRE_MINUTES
from app.domain.models.user import UserAuth, hash_password, EmailIsNotVerified, WrongPassword
from app.domain.services.session import SessionService, LoginDTO, UserWithEmailDoesntExists
from tests.unit.conftest import TUserRepo, TSessionRepo


@pytest.fixture(scope='function')
def session_service(user_repo: TUserRepo, session_repo: TSessionRepo) -> SessionService:
    return SessionService(
        user_repo=user_repo,
        session_repo=session_repo
    )


login_dto = LoginDTO(
    email='test@domain.com',
    password=b'qwerty123'
)


@pytest_asyncio.fixture(scope='function')
async def inserted_user(user_repo: TUserRepo) -> UserAuth:
    user = UserAuth.create(email=login_dto.email, hashed_password=hash_password(login_dto.password))
    user = await user_repo.insert(user)

    return user


@pytest_asyncio.fixture(scope='function')
async def access_and_refresh_token(
        session_service: SessionService,
        user_repo: TUserRepo,
        inserted_user: UserAuth
) -> Tuple[AccessToken, RefreshToken]:
    inserted_user.verify_email()
    await user_repo.update(inserted_user)

    return await session_service.login(login_dto)


@pytest.mark.asyncio
async def test_login(
        session_service: SessionService,
        user_repo: TUserRepo,
        session_repo: TSessionRepo,
        inserted_user: UserAuth
):
    with pytest.raises(UserWithEmailDoesntExists):
        await session_service.login(
            dto=LoginDTO(email='non_existing@domain.com', password=login_dto.password)
        )

    with pytest.raises(WrongPassword):
        await session_service.login(dto=LoginDTO(email=login_dto.email, password=b'wrong_password'))

    with pytest.raises(EmailIsNotVerified):
        await session_service.login(dto=login_dto)

    inserted_user.verify_email()
    await user_repo.update(inserted_user)

    access_token, refresh_token = await session_service.login(dto=login_dto)

    session = await session_repo.find_session_by_token(token=refresh_token.get_token())
    assert session.user_id == inserted_user.id


@pytest.mark.asyncio
async def test_refresh(
        session_repo: TSessionRepo,
        session_service: SessionService,
        access_and_refresh_token: Tuple[AccessToken, RefreshToken]
):
    access_token, refresh_token = access_and_refresh_token

    new_access_token, new_refresh_token = await session_service.refresh(refresh_token)

    assert new_access_token.get_token() != access_token.get_token()
    assert new_refresh_token.get_token() != refresh_token.get_token()

    with pytest.raises(ReusingOfRefreshToken):
        await session_service.refresh(refresh_token)

    # with Replace('app.domain.models.tokens.datetime', test_datetime(
    #         new_refresh_token.exp + datetime.timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES+1)
    # )):
    #     with pytest.raises(SessionIsNotActive):
    #         await session_service.refresh(refresh_token)

    session = await session_repo.find_session_by_token(refresh_token.get_token())
    session.status = SessionStatus.LOGOUT
    await session_repo.update(session)

    with pytest.raises(SessionIsNotActive):
        await session_service.refresh(refresh_token)
