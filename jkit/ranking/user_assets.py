from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit._normalization import normalize_assets_amount
from jkit.constraints import (
    NonNegativeFloat,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_convert import user_slug_to_url

if TYPE_CHECKING:
    from jkit.user import User


class _UserInfoField(DataObject, frozen=True):
    id: PositiveInt | None
    slug: UserSlug | None
    name: UserName | None
    avatar_url: UserUploadedUrl | None

    def to_user_obj(self) -> User:
        from jkit.user import User

        if not self.slug:
            raise ResourceUnavailableError(
                f"用户 {user_slug_to_url(self.slug)} 不存在或已注销 / 被封禁"
                if self.slug
                else "用户不存在或已注销 / 被封禁"
            )

        return User.from_slug(self.slug)._as_checked()


class RecordData(DataObject, frozen=True):
    ranking: PositiveInt
    assets_amount: NonNegativeFloat
    user_info: _UserInfoField


class UserAssetsRanking(ResourceObject):
    def __init__(self, *, start_ranking: int = 1) -> None:
        self._start_ranking = start_ranking

    async def iter_records(self) -> AsyncGenerator[RecordData, None]:
        current_id = self._start_ranking
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path="/asimov/fp_rankings",
                params={"since_id": current_id - 1, "max_id": 10**9},
                response_type="JSON",
            )
            if not data["rankings"]:
                return

            for item in data["rankings"]:
                yield RecordData(
                    ranking=item["ranking"],
                    assets_amount=normalize_assets_amount(item["amount"]),
                    user_info=_UserInfoField(
                        id=item["user"]["id"],
                        slug=item["user"]["slug"],
                        name=item["user"]["nickname"],
                        avatar_url=item["user"]["avatar"],
                    ),
                )._validate()

            current_id += len(data["rankings"])
