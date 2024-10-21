from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar

from httpx import HTTPStatusError

from jkit._base import (
    CheckableMixin,
    DataObject,
    IdAndUrlMixin,
    ResourceObject,
)
from jkit._network_request import get_json
from jkit._normalization import normalize_assets_amount, normalize_datetime
from jkit.config import CONFIG
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_notebook_id
from jkit.identifier_convert import notebook_id_to_url
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


class AuthorInfoField(DataObject, frozen=True, eq=True, kw_only=True):
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class NotebookInfo(DataObject, frozen=True, eq=True, kw_only=True):
    id: NotebookId
    name: NonEmptyStr
    description_updated_at: NormalizedDatetime
    author_info: AuthorInfoField

    articles_count: NonNegativeInt
    subscribers_count: NonNegativeInt
    total_wordage: NonNegativeInt


class ArticleAuthorInfoField(DataObject, frozen=True, eq=True, kw_only=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class NotebookArticleInfo(DataObject, frozen=True, eq=True, kw_only=True):
    id: PositiveInt
    slug: ArticleSlug
    title: NonEmptyStr
    description: str
    image_url: Optional[UserUploadedUrl]
    published_at: NormalizedDatetime
    is_paid: bool
    can_comment: bool
    author_info: ArticleAuthorInfoField

    views_count: NonNegativeInt
    likes_count: NonNegativeInt
    comments_count: NonNegativeInt
    tips_count: NonNegativeInt
    earned_fp_amount: NonNegativeFloat

    def to_article_obj(self) -> "Article":
        from jkit.article import Article

        return Article.from_slug(self.slug)._as_checked()


class Notebook(ResourceObject, CheckableMixin, IdAndUrlMixin):
    def __init__(self, *, id: int) -> None:  # noqa: A002
        super().__init__()
        self._checked = False

        if not is_notebook_id(id):
            raise ValueError(f"{id} 不是有效的文集 ID")
        self._id = id

    @classmethod
    def from_id(cls: type[T], id: int, /) -> T:  # noqa: A002
        return cls(id=id)

    @property
    def id(self) -> int:
        return self._id

    @property
    def url(self) -> str:
        return notebook_id_to_url(self._id)

    async def check(self) -> None:
        if self._checked:
            return

        try:
            await get_json(
                endpoint=CONFIG.endpoints.jianshu, path=f"/asimov/nb/{self.id}"
            )
            self._checked = True
        except HTTPStatusError:
            raise ResourceUnavailableError(f"文集 {self.url} 不存在或删除") from None

    @property
    async def info(self) -> NotebookInfo:
        await self._auto_check()

        data = await get_json(
            endpoint=CONFIG.endpoints.jianshu, path=f"/asimov/nb/{self.id}"
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
        order_by: Literal["add_time", "last_comment_time"] = "add_time",
        page_size: int = 20,
    ) -> AsyncGenerator[NotebookArticleInfo, None]:
        await self._auto_check()

        now_page = start_page
        while True:
            data: list[dict[str, Any]] = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path=f"/asimov/notebooks/{self.id}/public_notes",
                params={
                    "page": now_page,
                    "count": page_size,
                    "order_by": {
                        "add_time": "added_at",
                        "last_comment_time": "commented_at",
                    }[order_by],
                },
            )  # type: ignore

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
