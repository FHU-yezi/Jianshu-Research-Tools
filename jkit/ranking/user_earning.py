from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit._normalization import normalize_assets_amount
from jkit.constraints import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import APIUnsupportedError, ResourceUnavailableError

if TYPE_CHECKING:
    from jkit.user import User


class SummaryData(DataObject, frozen=True):
    fp_by_creating_amount_sum: PositiveFloat
    fp_by_voting_amount_sum: PositiveFloat
    total_fp_amount_sum: PositiveFloat


class RecordData(DataObject, frozen=True):
    ranking: PositiveInt
    name: UserName
    slug: UserSlug
    avatar_url: UserUploadedUrl
    total_fp_amount: PositiveFloat
    fp_by_creating_anount: NonNegativeFloat
    fp_by_voting_amount: NonNegativeFloat

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class UserEarningRanking(ResourceObject):
    def __init__(
        self,
        target_date: date | None = None,
        /,
    ) -> None:
        if not target_date:
            target_date = datetime.now().date() - timedelta(days=1)

        if target_date < date(2020, 6, 20):
            raise APIUnsupportedError("受 API 限制，无法获取 2020.06.20 前的排行榜数据")
        if target_date >= datetime.now().date():
            raise ResourceUnavailableError("无法获取未来的排行榜数据")

        self._target_date = target_date

    async def get_summary(self) -> SummaryData:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/fp_rankings/voter_users",
            params={
                "date": self._target_date.strftime(r"%Y%m%d"),
            },
            response_type="JSON",
        )

        return SummaryData(
            fp_by_creating_amount_sum=normalize_assets_amount(data["author_fp"]),
            fp_by_voting_amount_sum=normalize_assets_amount(data["voter_fp"]),
            total_fp_amount_sum=normalize_assets_amount(data["fp"]),
        )._validate()

    async def iter_records(
        self, *, type: Literal["ALL", "CREATING", "VOTING"]
    ) -> AsyncGenerator[RecordData, None]:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/fp_rankings/voter_users",
            params={
                "type": {"ALL": None, "CREATING": "note", "VOTING": "like"}[type],
                "date": self._target_date.strftime(r"%Y%m%d"),
            },
            response_type="JSON",
        )

        for ranking, item in enumerate(data["users"], start=1):
            yield RecordData(
                ranking=ranking,
                name=item["nickname"],
                slug=item["slug"],
                avatar_url=item["avatar"],
                total_fp_amount=normalize_assets_amount(item["fp"]),
                fp_by_creating_anount=normalize_assets_amount(item["author_fp"]),
                fp_by_voting_amount=normalize_assets_amount(item["voter_fp"]),
            )._validate()
