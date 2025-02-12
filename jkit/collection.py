from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import (
    TYPE_CHECKING,
    Literal,
)

from httpx import HTTPStatusError

from jkit._base import (
    CheckableResourceMixin,
    DataObject,
    ResourceObject,
    SlugAndUrlResourceMixin,
)
from jkit._network import send_request
from jkit._normalization import normalize_assets_amount, normalize_datetime
from jkit.constants import _RESOURCE_UNAVAILABLE_STATUS_CODE
from jkit.constraints import (
    ArticleSlug,
    CollectionSlug,
    NonEmptyStr,
    NonNegativeFloat,
    NonNegativeInt,
    NormalizedDatetime,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_collection_slug, is_collection_url
from jkit.identifier_convert import collection_slug_to_url, collection_url_to_slug

if TYPE_CHECKING:
    from jkit.article import Article
    from jkit.user import User


class _OwnerInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class InfoData(DataObject, frozen=True):
    id: PositiveInt
    slug: CollectionSlug
    name: NonEmptyStr
    image_url: UserUploadedUrl
    description: str
    description_update_time: NormalizedDatetime
    # TODO: 修改变量名
    latest_add_article_time: NormalizedDatetime
    owner_info: _OwnerInfoField

    articles_count: NonNegativeInt
    subscribers_count: NonNegativeInt


class _ArticleAuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class ArticleData(DataObject, frozen=True):
    id: PositiveInt
    slug: ArticleSlug
    title: NonEmptyStr
    description: str
    image_url: UserUploadedUrl | None
    publish_time: NormalizedDatetime
    is_paid: bool
    can_comment: bool
    author_info: _ArticleAuthorInfoField

    views_count: NonNegativeInt
    likes_count: NonNegativeInt
    comments_count: NonNegativeInt
    tips_count: NonNegativeInt
    earned_fp_amount: NonNegativeFloat

    def to_article_obj(self) -> Article:
        from jkit.article import Article

        return Article.from_slug(self.slug)._as_checked()


class Collection(ResourceObject, SlugAndUrlResourceMixin, CheckableResourceMixin):
    _resource_readable_name = "专题"

    _slug_check_func = is_collection_slug
    _url_check_func = is_collection_url

    _url_to_slug_func = collection_url_to_slug
    _slug_to_url_func = collection_slug_to_url

    def __init__(self, *, slug: str | None = None, url: str | None = None) -> None:
        SlugAndUrlResourceMixin.__init__(self, slug=slug, url=url)
        CheckableResourceMixin.__init__(self)

    def __repr__(self) -> str:
        return SlugAndUrlResourceMixin.__repr__(self)

    async def check(self) -> None:
        try:
            await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/collections/slug/{self.slug}",
                response_type="JSON",
            )
        except HTTPStatusError as e:
            if e.response.status_code == _RESOURCE_UNAVAILABLE_STATUS_CODE:
                raise ResourceUnavailableError(
                    f"专题 {self.url} 不存在或已被删除"
                ) from None

            raise
        else:
            self._checked = True

    @property
    async def info(self) -> InfoData:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/asimov/collections/slug/{self.slug}",
            response_type="JSON",
        )

        return InfoData(
            id=data["id"],
            slug=data["slug"],
            name=data["title"],
            image_url=data["image"],
            description=data["content_in_full"],
            description_update_time=normalize_datetime(data["last_updated_at"]),
            latest_add_article_time=normalize_datetime(data["newly_added_at"]),
            owner_info=_OwnerInfoField(
                id=data["owner"]["id"],
                slug=data["owner"]["slug"],
                name=data["owner"]["nickname"],
            ),
            articles_count=data["notes_count"],
            subscribers_count=data["subscribers_count"],
        )._validate()

    async def iter_articles(
        self,
        *,
        start_page: int = 1,
        order_by: Literal["ADD_TIME", "LAST_COMMENT_TIME", "POPULARITY"] = "ADD_TIME",
    ) -> AsyncGenerator[ArticleData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/collections/slug/{self.slug}/public_notes",
                params={
                    "page": current_page,
                    "count": 20,
                    "ordered_by": {
                        "ADD_TIME": "time",
                        "LAST_COMMENT_TIME": "comment_time",
                        "POPULARITY": "hot",
                    }[order_by],
                },
                response_type="JSON_LIST",
            )
            if not data:
                return

            for item in data:
                yield ArticleData(
                    id=item["object"]["data"]["id"],
                    slug=item["object"]["data"]["slug"],
                    title=item["object"]["data"]["title"],
                    description=item["object"]["data"]["public_abbr"],
                    image_url=item["object"]["data"]["list_image_url"]
                    if item["object"]["data"]["list_image_url"]
                    else None,
                    publish_time=normalize_datetime(
                        item["object"]["data"]["first_shared_at"]
                    ),
                    is_paid=item["object"]["data"]["paid"],
                    can_comment=item["object"]["data"]["commentable"],
                    author_info=_ArticleAuthorInfoField(
                        id=item["object"]["data"]["user"]["id"],
                        slug=item["object"]["data"]["user"]["slug"],
                        name=item["object"]["data"]["user"]["nickname"],
                        avatar_url=item["object"]["data"]["user"]["avatar"],
                    ),
                    views_count=item["object"]["data"]["views_count"],
                    likes_count=item["object"]["data"]["likes_count"],
                    comments_count=item["object"]["data"]["public_comments_count"],
                    tips_count=item["object"]["data"]["total_rewards_count"],
                    earned_fp_amount=normalize_assets_amount(
                        item["object"]["data"]["total_fp_amount"]
                    ),
                )._validate()

            current_page += 1
