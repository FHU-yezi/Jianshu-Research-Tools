from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit._normalization import normalize_datetime
from jkit.msgspec_constraints import (
    NonEmptyStr,
    NormalizedDatetime,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)

if TYPE_CHECKING:
    from jkit.user import User


class UserInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class LotteryWinRecord(DataObject, frozen=True):
    id: PositiveInt
    time: NormalizedDatetime
    award_name: NonEmptyStr

    user_info: UserInfoField


class Lottery(ResourceObject):
    async def iter_win_records(
        self, *, count: int = 100
    ) -> AsyncGenerator[LotteryWinRecord, None]:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/ad_rewards/winner_list",
            body={"count": count},
            response_type="JSON_LIST",
        )

        for item in data:
            yield LotteryWinRecord(
                id=item["id"],
                time=normalize_datetime(item["created_at"]),
                award_name=item["name"],
                user_info=UserInfoField(
                    id=item["user"]["id"],
                    slug=item["user"]["slug"],
                    name=item["user"]["nickname"],
                    avatar_url=item["user"]["avatar"],
                ),
            )._validate()
