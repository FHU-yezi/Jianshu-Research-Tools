from __future__ import annotations

from jkit._base import CredentialObject


class JianshuCredential(CredentialObject):
    def __init__(self, *, remember_user_token: str) -> None:
        self._remember_user_token = remember_user_token

    @classmethod
    def from_remember_user_token(cls, remember_user_token: str, /) -> JianshuCredential:
        return cls(remember_user_token=remember_user_token)

    @property
    def headers(self) -> dict[str, str]:
        return {"Cookie": f"remember_user_token={self._remember_user_token}"}


class BeijiaoyiCredential(CredentialObject):
    def __init__(self, *, bearer_token: str) -> None:
        self._bearer_token = bearer_token

    @classmethod
    def from_bearer_token(cls, bearer_token: str, /) -> BeijiaoyiCredential:
        return cls(bearer_token=bearer_token)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._bearer_token}"}
