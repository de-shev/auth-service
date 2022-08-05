from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.session import Session


class ISessionRepo(ABC):
    @abstractmethod
    async def insert(self, session: Session) -> Session: ...

    @abstractmethod
    async def update(self, session: Session): ...

    @abstractmethod
    async def find_session_by_id(self, _id: str, user_id: str) -> Optional[Session]: ...

    @abstractmethod
    async def find_session_by_token(self, token: str) -> Optional[Session]: ...

    @abstractmethod
    async def invalidate_session_family(self, session: Session): ...