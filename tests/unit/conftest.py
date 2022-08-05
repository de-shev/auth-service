import asyncio
from typing import Optional, Callable, Any, TypeVar, Dict

import pytest
from bson import ObjectId
from pydantic import BaseModel

from app.common_lib.domain.model import ID
from app.common_lib.executor import IAsyncExecutor
from app.domain.models.session import Session
from app.domain.repos.session import ISessionRepo
from app.domain.models.user import UserAuth
from app.domain.models.verification_code import VerificationCode
from app.domain.repos.verification_code import IVerificationCodeRepo
from app.domain.repos.user import IUserAuthRepo

ObjType = TypeVar('ObjType', bound=BaseModel)


class TRepo:
    @classmethod
    def _get_object_from_store(cls, store: Dict[Any, ObjType], key: Any) -> Optional[ObjType]:
        obj = store.get(key)
        if obj:
            return obj.copy(deep=True)
        return None


class TUserRepo(IUserAuthRepo, TRepo):

    def __init__(self):
        self._id_to_user = {}
        self._email_to_user = {}

    def _update_store(self, user: UserAuth):
        self._id_to_user[user.id] = user
        self._email_to_user[user.email] = user

    async def does_user_exists(self, email: str) -> bool:
        return email in self._email_to_user

    async def find_by_id(self, _id: str) -> Optional[UserAuth]:
        return self._get_object_from_store(self._id_to_user, ObjectId(_id))

    async def find_by_email(self, email: str) -> Optional[UserAuth]:
        return self._get_object_from_store(self._email_to_user, email)

    async def insert(self, user: UserAuth) -> UserAuth:
        user.id = ObjectId()
        self._update_store(user)

        return user

    async def update(self, user: UserAuth):
        self._update_store(user)


@pytest.fixture(scope='function')
def user_repo() -> TUserRepo:
    return TUserRepo()


class TVerCodeRepo(IVerificationCodeRepo, TRepo):
    def __init__(self):
        self._user_id_to_ver_code = {}

    def _update_store(self, ver_code: VerificationCode):
        self._user_id_to_ver_code[ver_code.id] = ver_code

    async def find_by_user_id(self, user_id: str) -> Optional[VerificationCode]:
        return self._get_object_from_store(self._user_id_to_ver_code, ObjectId(user_id))

    async def insert(self, ver_code: VerificationCode):
        self._update_store(ver_code)

    async def update(self, ver_code: VerificationCode):
        self._update_store(ver_code)


@pytest.fixture(scope='function')
def ver_code_repo() -> TVerCodeRepo:
    return TVerCodeRepo()


class TSessionRepo(ISessionRepo, TRepo):
    def __init__(self):
        self._id_to_session = {}
        self._token_to_session = {}

    def _update_store(self, session: Session):
        self._id_to_session[session.id] = session
        self._token_to_session[session.refresh_token] = session

    async def insert(self, session: Session) -> Session:
        session.id = ObjectId()
        self._update_store(session)

        return session

    async def update(self, session: Session):
        self._update_store(session)

    async def find_session_by_id(self, _id: str) -> Optional[Session]:
        return self._get_object_from_store(self._id_to_session, ObjectId(_id))

    async def find_session_by_token(self, token: str) -> Optional[Session]:
        return self._get_object_from_store(self._token_to_session, token)

    async def invalidate_session_family(self, session: Session):
        pass


@pytest.fixture(scope='function')
def session_repo() -> TSessionRepo:
    return TSessionRepo()


class AsyncExecutor(IAsyncExecutor):

    async def __call__(self, func: Callable) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)
