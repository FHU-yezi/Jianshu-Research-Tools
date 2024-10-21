from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from jkit._base import DataObject, ResourceObject
from jkit._network_request import get_json
from jkit.config import CONFIG
from jkit.msgspec_constraints import PositiveInt, UserName, UserSlug, UserUploadedUrl

if TYPE_CHECKING:
    from jkit.user import User


class UserInfoField(DataObject, frozen=True, eq=True, kw_only=True):
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class DailyUpdateRankingRecord(DataObject, frozen=True, eq=True, kw_only=True):
    ranking: PositiveInt
    days: PositiveInt
    user_info: UserInfoField


class DailyUpdateRanking(ResourceObject):
    async def __aiter__(self) -> AsyncGenerator[DailyUpdateRankingRecord, None]:
        data = await get_json(
            endpoint=CONFIG.endpoints.jianshu,
            path="/asimov/daily_activity_participants/rank",
        )

        for item in data["daps"]:
            yield DailyUpdateRankingRecord(
                ranking=item["rank"],
                days=item["checkin_count"],
                user_info=UserInfoField(
                    slug=item["slug"],
                    name=item["nickname"],
                    avatar_url=item["avatar"],
                ),
            )._validate()
