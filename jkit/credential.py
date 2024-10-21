from jkit._base import ResourceObject


class JianshuCredential(ResourceObject):
    def __init__(self, *, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        return self._token

    @property
    def cookies(self) -> dict[str, str]:
        return {"remember_user_token": self.token}
