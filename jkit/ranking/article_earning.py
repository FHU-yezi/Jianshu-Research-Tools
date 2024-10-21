from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Optional

from jkit._base import DATA_OBJECT_CONFIG, DataObject, ResourceObject
from jkit._network_request import get_json
from jkit._normalization import normalize_assets_amount
from jkit.config import CONFIG
from jkit.exceptions import APIUnsupportedError
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


class AuthorInfoField(DataObject, **DATA_OBJECT_CONFIG):
    name: Optional[UserName]
    avatar_url: Optional[UserUploadedUrl]


class RecordField(DataObject, **DATA_OBJECT_CONFIG):
    ranking: PositiveInt
    title: Optional[NonEmptyStr]
    slug: Optional[ArticleSlug]
    total_fp_amount: PositiveFloat
    fp_to_author_anount: PositiveFloat
    fp_to_voter_amount: PositiveFloat
    author_info: AuthorInfoField

    @property
    def is_missing(self) -> bool:
        return not bool(self.slug)

    def to_article_obj(self) -> "Article":
        if not self.slug:
            raise APIUnsupportedError("文章走丢了，可能已被作者删除 / 私密或被锁定")

        from jkit.article import Article

        return Article.from_slug(self.slug)._as_checked()


class ArticleEarningRankingData(DataObject, **DATA_OBJECT_CONFIG):
    total_fp_amount_sum: PositiveFloat
    fp_to_author_amount_sum: PositiveFloat
    fp_to_voter_amount_sum: PositiveFloat
    records: tuple[RecordField, ...]


class ArticleEarningRanking(ResourceObject):
    def __init__(self, target_date: Optional[date] = None, /) -> None:
        if not target_date:
            target_date = datetime.now().date() - timedelta(days=1)

        if target_date < date(2020, 6, 20):
            raise APIUnsupportedError("不支持获取 2020.06.20 前的排行榜数据")
        if target_date >= datetime.now().date():
            raise ValueError("不支持获取未来的排行榜数据")

        self._target_date = target_date

    async def get_data(self) -> ArticleEarningRankingData:
        data = await get_json(
            endpoint=CONFIG.endpoints.jianshu,
            path="/asimov/fp_rankings/voter_notes",
            params={"date": self._target_date.strftime(r"%Y%m%d")},
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
