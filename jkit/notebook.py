from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Literal, TypeVar

from httpx import HTTPStatusError

from jkit._base import (
    CheckableResourceMixin,
    DataObject,
    IdAndUrlResourceMixin,
    ResourceObject,
)
from jkit._network import send_request
from jkit._normalization import normalize_assets_amount, normalize_datetime
from jkit.constants import _RESOURCE_UNAVAILABLE_STATUS_CODE
from jkit.constraints import (
    ArticleSlug,
    NonEmptyStr,
    NonNegativeFloat,
    NonNegativeInt,
    NormalizedDatetime,
    NotebookId,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_notebook_id, is_notebook_url
from jkit.identifier_convert import notebook_id_to_url, notebook_url_to_id

if TYPE_CHECKING:
    from jkit.article import Article
    from jkit.user import User

T = TypeVar("T", bound="Notebook")


class _AuthorInfoField(DataObject, frozen=True):
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class InfoData(DataObject, frozen=True):
    id: NotebookId
    name: NonEmptyStr
    description_update_time: NormalizedDatetime
    author_info: _AuthorInfoField

    articles_count: NonNegativeInt
    subscribers_count: NonNegativeInt
    total_wordage: NonNegativeInt


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


class Notebook(ResourceObject, IdAndUrlResourceMixin, CheckableResourceMixin):
    _resource_readable_name = "文集"

    _id_check_func = is_notebook_id
    _url_check_func = is_notebook_url

    _url_to_id_func = notebook_url_to_id
    _id_to_url_func = notebook_id_to_url

    def __init__(self, *, id: int | None = None, url: str | None = None) -> None:
        IdAndUrlResourceMixin.__init__(self, id=id, url=url)
        CheckableResourceMixin.__init__(self)

    def __repr__(self) -> str:
        return IdAndUrlResourceMixin.__repr__(self)

    async def check(self) -> None:
        try:
            await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/nb/{self.id}",
                response_type="JSON",
            )
        except HTTPStatusError as e:
            if e.response.status_code == _RESOURCE_UNAVAILABLE_STATUS_CODE:
                raise ResourceUnavailableError(
                    f"文集 {self.url} 不存在或已被删除"
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
            path=f"/asimov/nb/{self.id}",
            response_type="JSON",
        )

        return InfoData(
            id=data["id"],
            name=data["name"],
            description_update_time=normalize_datetime(data["last_updated_at"]),
            author_info=_AuthorInfoField(
                slug=data["user"]["slug"],
                name=data["user"]["nickname"],
                avatar_url=data["user"]["avatar"],
            ),
            articles_count=data["notes_count"],
            subscribers_count=data["subscribers_count"],
            total_wordage=data["wordage"],
        )._validate()

    async def iter_articles(
        self,
        *,
        start_page: int = 1,
        order_by: Literal["ADD_TIME", "LAST_COMMENT_TIME"] = "ADD_TIME",
    ) -> AsyncGenerator[ArticleData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/notebooks/{self.id}/public_notes",
                params={
                    "page": current_page,
                    "count": 20,
                    "order_by": {
                        "ADD_TIME": "added_at",
                        "LAST_COMMENT_TIME": "commented_at",
                    }[order_by],
                },
                response_type="JSON_LIST",
            )

            if not data:
                return

            for item in data:
                item = item["object"]["data"]  # noqa: PLW2901

                yield ArticleData(
                    id=item["id"],
                    slug=item["slug"],
                    title=item["title"],
                    description=item["public_abbr"],
                    image_url=item["list_image_url"]
                    if item["list_image_url"]
                    else None,
                    publish_time=normalize_datetime(item["first_shared_at"]),
                    is_paid=item["paid"],
                    can_comment=item["commentable"],
                    author_info=_ArticleAuthorInfoField(
                        id=item["user"]["id"],
                        slug=item["user"]["slug"],
                        name=item["user"]["nickname"],
                        avatar_url=item["user"]["avatar"],
                    ),
                    views_count=item["views_count"],
                    likes_count=item["likes_count"],
                    comments_count=item["public_comments_count"],
                    tips_count=item["total_rewards_count"],
                    earned_fp_amount=normalize_assets_amount(item["total_fp_amount"]),
                )._validate()

            current_page += 1
