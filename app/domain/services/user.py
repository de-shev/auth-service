from dataclasses import dataclass

from app.common_lib.errors import AppError, InternalError
from app.common_lib.executor import IAsyncExecutor
from app.domain.models.tokens import RegistrationToken
from app.domain.models.user import UserAuth, hash_password
from app.domain.repos.user import IUserAuthRepo
from app.domain.models.verification_code import VerificationCode
from app.domain.repos.verification_code import IVerificationCodeRepo


class UserDoesntExistsButHaveTo(InternalError):
    pass


class UserAlreadyExists(AppError):
    pass


@dataclass
class RegisterDTO:
    email: str
    password: bytes


@dataclass
class VerifyEmailDTO:
    code: str


class UserService:
    def __init__(
            self,
            user_repo: IUserAuthRepo,
            ver_code_repo: IVerificationCodeRepo,
            executor: IAsyncExecutor,
            email_service
    ):
        self._user_repo = user_repo
        self._ver_code_repo = ver_code_repo
        self._executor = executor
        self._email_service = email_service

    async def register(self, dto: RegisterDTO) -> RegistrationToken:
        if await self._user_repo.does_user_exists(email=dto.email):
            raise UserAlreadyExists()

        hashed_password = await self._executor(lambda: hash_password(dto.password))

        user = UserAuth.create(email=dto.email, hashed_password=hashed_password)
        user = await self._user_repo.insert(user)

        return RegistrationToken.create(user)

    async def _find_existing_user_by_id(self, user_id: str) -> UserAuth:
        user = await self._user_repo.find_by_id(_id=user_id)
        if not user:
            raise UserDoesntExistsButHaveTo()

        return user

    async def send_user_verification_email(self, token: RegistrationToken):
        user = await self._find_existing_user_by_id(user_id=token.sub)
        user.check_is_email_not_verified()

        ver_code = await self._ver_code_repo.find_by_user_id(user.id)

        if ver_code:
            ver_code.update_for_resend()
            await self._ver_code_repo.update(ver_code)
        else:
            ver_code = VerificationCode.create(user)
            await self._ver_code_repo.insert(ver_code)

        # TODO send email

    async def verify_email(self, token: RegistrationToken, dto: VerifyEmailDTO):
        user = await self._find_existing_user_by_id(user_id=token.sub)

        user.check_is_email_not_verified()

        ver_code = await self._ver_code_repo.find_by_user_id(user.id)
        ver_code.check_code(code=dto.code)

        user.verify_email()
        await self._user_repo.update(user)
