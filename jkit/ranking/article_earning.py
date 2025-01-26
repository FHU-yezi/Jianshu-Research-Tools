from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit._normalization import normalize_assets_amount
from jkit.exceptions import APIUnsupportedError
from jkit.identifier_convert import article_slug_to_url
from jkit.msgspec_constraints import (
    ArticleSlug,
    NonEmptyStr,
    PositiveFloat,
    PositiveInt,
    UserName,
    UserUploadedUrl,
)

if TYPE_CHECKING:
    from jkit.article import Article


class AuthorInfoField(DataObject, frozen=True):
    name: UserName | None
    avatar_url: UserUploadedUrl | None


class RecordField(DataObject, frozen=True):
    ranking: PositiveInt
    title: NonEmptyStr | None
    slug: ArticleSlug | None
    total_fp_amount: PositiveFloat
    fp_to_author_anount: PositiveFloat
    fp_to_voter_amount: PositiveFloat
    author_info: AuthorInfoField

    @property
    def is_missing(self) -> bool:
        return not bool(self.slug)

    def to_article_obj(self) -> Article:
        if not self.slug:
            raise APIUnsupportedError(
                f"文章 {article_slug_to_url(self.slug)} 不存在或已被删除 / 私密 / 锁定"
                if self.slug
                else "文章不存在或已被删除 / 私密 / 锁定"
            )

        from jkit.article import Article

        return Article.from_slug(self.slug)._as_checked()


class ArticleEarningRankingData(DataObject, frozen=True):
    total_fp_amount_sum: PositiveFloat
    fp_to_author_amount_sum: PositiveFloat
    fp_to_voter_amount_sum: PositiveFloat
    records: tuple[RecordField, ...]


class ArticleEarningRanking(ResourceObject):
    def __init__(self, target_date: date | None = None, /) -> None:
        if not target_date:
            target_date = datetime.now().date() - timedelta(days=1)

        if target_date < date(2020, 6, 20):
            raise APIUnsupportedError("受 API 限制，无法获取 2020.06.20 前的排行榜数据")
        if target_date >= datetime.now().date():
            raise ValueError("无法获取未来的排行榜数据")

        self._target_date = target_date

    async def get_data(self) -> ArticleEarningRankingData:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/fp_rankings/voter_notes",
            body={"date": self._target_date.strftime(r"%Y%m%d")},
            response_type="JSON",
        )

        return ArticleEarningRankingData(
            total_fp_amount_sum=normalize_assets_amount(data["fp"]),
            fp_to_author_amount_sum=normalize_assets_amount(data["author_fp"]),
            fp_to_voter_amount_sum=normalize_assets_amount(data["voter_fp"]),
            records=tuple(
                RecordField(
                    ranking=ranking,
                    title=item["title"],
                    slug=item["slug"],
                    total_fp_amount=normalize_assets_amount(item["fp"]),
                    fp_to_author_anount=normalize_assets_amount(item["author_fp"]),
                    fp_to_voter_amount=normalize_assets_amount(item["voter_fp"]),
                    author_info=AuthorInfoField(
                        name=item["author_nickname"],
                        avatar_url=item["author_avatar"],
                    ),
                )
                for ranking, item in enumerate(data["notes"], start=1)
            ),
        )._validate()

    async def __aiter__(self) -> AsyncGenerator[RecordField, None]:
        for item in (await self.get_data()).records:
            yield item
