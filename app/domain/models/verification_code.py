from datetime import datetime, timedelta
from random import randint

from app.common_lib.domain.model import IdModel
from app.common_lib.errors import AppError
from app.domain.models.user import UserAuth

CODE_LEN = 6
VERIFICATION_CODE_EXPIRE_MINUTES = 10
VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS = 60


class VerCodeCooldownIsNotOver(AppError):
    pass


class VerCodeIsNotCorrect(AppError):
    pass


class VerCodeIsExpired(AppError):
    pass


def _generate_six_digit_code() -> str:
    return str(randint(99999, 999999))


class VerificationCode(IdModel):
    code: str
    issue_date: datetime
    exp_date: datetime

    @staticmethod
    def _generate_code() -> str:
        return _generate_six_digit_code()

    @classmethod
    def create(cls, user: UserAuth):
        issue_date = datetime.now()
        return cls(
            id=user.id,
            code=cls._generate_code(),
            issue_date=issue_date,
            exp_date=issue_date + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
        )

    def update_for_resend(self):
        if self.issue_date + timedelta(seconds=VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS) > datetime.now():
            raise VerCodeCooldownIsNotOver()

        self.code = _generate_six_digit_code()
        self.issue_date = datetime.now()
        self.exp_date = self.issue_date + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)

    def check_code(self, code: str):
        if self.exp_date < datetime.now():
            raise VerCodeIsExpired()

        if self.code != code:
            raise VerCodeIsNotCorrect()
