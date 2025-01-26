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
from jkit.exceptions import APIUnsupportedError

if TYPE_CHECKING:
    from jkit.user import User


class RecordField(DataObject, frozen=True):
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


class UserEarningRankingData(DataObject, frozen=True):
    total_fp_amount_sum: PositiveFloat
    fp_by_creating_amount_sum: PositiveFloat
    fp_by_voting_amount_sum: PositiveFloat
    records: tuple[RecordField, ...]


class UserEarningRanking(ResourceObject):
    def __init__(
        self,
        target_date: date | None = None,
        /,
        *,
        type: Literal["all", "creating", "voting"] = "all",
    ) -> None:
        if not target_date:
            target_date = datetime.now().date() - timedelta(days=1)

        if target_date < date(2020, 6, 20):
            raise APIUnsupportedError("受 API 限制，无法获取 2020.06.20 前的排行榜数据")
        if target_date >= datetime.now().date():
            raise ValueError("无法获取未来的排行榜数据")

        self._target_date = target_date
        self._type = type

    async def get_data(self) -> UserEarningRankingData:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/fp_rankings/voter_users",
            body={
                "type": {"all": None, "creating": "note", "voting": "like"}[self._type],
                "date": self._target_date.strftime(r"%Y%m%d"),
            },
            response_type="JSON",
        )

        return UserEarningRankingData(
            total_fp_amount_sum=normalize_assets_amount(data["fp"]),
            fp_by_creating_amount_sum=normalize_assets_amount(data["author_fp"]),
            fp_by_voting_amount_sum=normalize_assets_amount(data["voter_fp"]),
            records=tuple(
                RecordField(
                    ranking=ranking,
                    name=item["nickname"],
                    slug=item["slug"],
                    avatar_url=item["avatar"],
                    total_fp_amount=normalize_assets_amount(item["fp"]),
                    fp_by_creating_anount=normalize_assets_amount(item["author_fp"]),
                    fp_by_voting_amount=normalize_assets_amount(item["voter_fp"]),
                )
                for ranking, item in enumerate(data["users"], start=1)
            ),
        )._validate()

    async def __aiter__(self) -> AsyncGenerator[RecordField, None]:
        for item in (await self.get_data()).records:
            yield item
