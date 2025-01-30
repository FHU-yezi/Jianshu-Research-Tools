from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit.constraints import PositiveInt, UserName, UserSlug, UserUploadedUrl

if TYPE_CHECKING:
    from jkit.user import User


class _UserInfoField(DataObject, frozen=True):
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class RecordData(DataObject, frozen=True):
    ranking: PositiveInt
    days: PositiveInt
    user_info: _UserInfoField


class DailyUpdateRanking(ResourceObject):
    async def iter_records(self) -> AsyncGenerator[RecordData, None]:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/daily_activity_participants/rank",
            response_type="JSON",
        )

        for item in data["daps"]:
            yield RecordData(
                ranking=item["rank"],
                days=item["checkin_count"],
                user_info=_UserInfoField(
                    slug=item["slug"],
                    name=item["nickname"],
                    avatar_url=item["avatar"],
                ),
            )._validate()
