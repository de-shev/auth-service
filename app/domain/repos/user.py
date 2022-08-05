from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.user import UserAuth


class IUserAuthRepo(ABC):

    @abstractmethod
    async def does_user_exists(self, email: str) -> bool: ...

    @abstractmethod
    async def find_by_id(self, _id: str) -> Optional[UserAuth]: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[UserAuth]: ...

    @abstractmethod
    async def insert(self, user: UserAuth) -> UserAuth: ...

    @abstractmethod
    async def update(self, user: UserAuth): ...


