from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.verification_code import VerificationCode


class IVerificationCodeRepo(ABC):
    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[VerificationCode]:
        ...

    @abstractmethod
    async def insert(self, ver_code: VerificationCode):
        ...

    @abstractmethod
    async def update(self, ver_code: VerificationCode):
        ...