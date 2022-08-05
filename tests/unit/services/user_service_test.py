import datetime

import pytest
from testfixtures import Replace, test_datetime

from app.domain.models.user import WrongPassword, EmailIsNotVerified, EmailIsAlreadyVerified
from app.domain.models.verification_code import VerCodeCooldownIsNotOver, VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS, \
    _generate_six_digit_code, \
    VerCodeIsNotCorrect, VerCodeIsExpired
from app.domain.services.user import UserService, RegisterDTO, UserAlreadyExists, VerifyEmailDTO
from tests.unit.conftest import TUserRepo, TVerCodeRepo, AsyncExecutor


@pytest.fixture(scope='function')
def user_service(user_repo: TUserRepo, ver_code_repo: TVerCodeRepo) -> UserService:
    return UserService(
        user_repo=user_repo,
        ver_code_repo=ver_code_repo,
        email_service=None,
        executor=AsyncExecutor()
    )


register_dto = RegisterDTO(
    email='test@domain.com',
    password=b'qwerty123'
)


@pytest.mark.asyncio
async def test_register(user_service: UserService, user_repo: TUserRepo):
    token = await user_service.register(register_dto)

    user = await user_repo.find_by_id(token.sub)

    user.check_password(register_dto.password)

    with pytest.raises(WrongPassword):
        await user.check_password(b'wrong_password')

    with pytest.raises(EmailIsNotVerified):
        user.check_can_user_login(register_dto.password)

    with pytest.raises(UserAlreadyExists):
        await user_service.register(register_dto)


@pytest.mark.asyncio
async def test_send_user_verification_email(
        user_service: UserService,
        ver_code_repo: TVerCodeRepo,
        user_repo: TUserRepo
):
    token = await user_service.register(register_dto)

    await user_service.send_user_verification_email(token)
    ver_code = await ver_code_repo.find_by_user_id(token.sub)

    with pytest.raises(VerCodeCooldownIsNotOver):
        await user_service.send_user_verification_email(token)

    with Replace('app.domain.models.verification_code.datetime', test_datetime(
            ver_code.issue_date + datetime.timedelta(seconds=VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS + 1)
    )):
        await user_service.send_user_verification_email(token)
        resented_ver_code = await ver_code_repo.find_by_user_id(token.sub)

    assert ver_code.id == resented_ver_code.id
    assert ver_code.code != resented_ver_code.code
    assert ver_code.issue_date != resented_ver_code.issue_date
    assert ver_code.exp_date != resented_ver_code.exp_date

    user = await user_repo.find_by_id(_id=token.sub)
    user.is_email_verified = True
    await user_repo.update(user)

    with pytest.raises(EmailIsAlreadyVerified):
        await user_service.send_user_verification_email(token)


def generate_wrong_code(right_code: str):
    while True:
        wrong_code = _generate_six_digit_code()
        if wrong_code != right_code:
            return wrong_code


@pytest.mark.asyncio
async def test_verify_email(
        user_service: UserService,
        ver_code_repo: TVerCodeRepo,
        user_repo: TUserRepo
):
    token = await user_service.register(register_dto)

    await user_service.send_user_verification_email(token)

    ver_code = await ver_code_repo.find_by_user_id(token.sub)

    with pytest.raises(VerCodeIsNotCorrect):
        await user_service.verify_email(token, VerifyEmailDTO(code=generate_wrong_code(ver_code.code)))

    with Replace('app.domain.models.verification_code.datetime', test_datetime(
            ver_code.exp_date + datetime.timedelta(seconds=1)
    )):
        with pytest.raises(VerCodeIsExpired):
            await user_service.verify_email(token, VerifyEmailDTO(code=ver_code.code))

    await user_service.verify_email(token, VerifyEmailDTO(code=ver_code.code))

    user = await user_repo.find_by_id(_id=token.sub)
    user.check_can_user_login(password=register_dto.password)

    with pytest.raises(EmailIsAlreadyVerified):
        await user_service.verify_email(token, VerifyEmailDTO(code=ver_code.code))
