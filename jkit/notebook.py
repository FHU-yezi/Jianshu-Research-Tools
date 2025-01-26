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
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_notebook_id, is_notebook_url
from jkit.identifier_convert import notebook_id_to_url, notebook_url_to_id
from jkit.msgspec_constraints import (
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

if TYPE_CHECKING:
    from jkit.article import Article
    from jkit.user import User

T = TypeVar("T", bound="Notebook")


class AuthorInfoField(DataObject, frozen=True):
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class NotebookInfo(DataObject, frozen=True):
    id: NotebookId
    name: NonEmptyStr
    description_updated_at: NormalizedDatetime
    author_info: AuthorInfoField

    articles_count: NonNegativeInt
    subscribers_count: NonNegativeInt
    total_wordage: NonNegativeInt


class ArticleAuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class NotebookArticleInfo(DataObject, frozen=True):
    id: PositiveInt
    slug: ArticleSlug
    title: NonEmptyStr
    description: str
    image_url: UserUploadedUrl | None
    published_at: NormalizedDatetime
    is_paid: bool
    can_comment: bool
    author_info: ArticleAuthorInfoField

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
    async def info(self) -> NotebookInfo:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/asimov/nb/{self.id}",
            response_type="JSON",
        )

        return NotebookInfo(
            id=data["id"],
            name=data["name"],
            description_updated_at=normalize_datetime(data["last_updated_at"]),
            author_info=AuthorInfoField(
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
        page_size: int = 20,
    ) -> AsyncGenerator[NotebookArticleInfo, None]:
        await self._require_check()

        now_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/notebooks/{self.id}/public_notes",
                body={
                    "page": now_page,
                    "count": page_size,
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
                yield NotebookArticleInfo(
                    id=item["object"]["data"]["id"],
                    slug=item["object"]["data"]["slug"],
                    title=item["object"]["data"]["title"],
                    description=item["object"]["data"]["public_abbr"],
                    image_url=item["object"]["data"]["list_image_url"]
                    if item["object"]["data"]["list_image_url"]
                    else None,
                    published_at=normalize_datetime(
                        item["object"]["data"]["first_shared_at"]
                    ),
                    is_paid=item["object"]["data"]["paid"],
                    can_comment=item["object"]["data"]["commentable"],
                    author_info=ArticleAuthorInfoField(
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

            now_page += 1
