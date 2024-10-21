from collections.abc import AsyncGenerator
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
)

from httpx import HTTPStatusError

from jkit._base import (
    CheckableMixin,
    DataObject,
    ResourceObject,
    SlugAndUrlMixin,
)
from jkit._network_request import get_json
from jkit._normalization import normalize_assets_amount, normalize_datetime
from jkit.config import CONFIG
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_collection_slug
from jkit.identifier_convert import collection_slug_to_url, collection_url_to_slug
from jkit.msgspec_constraints import (
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

if TYPE_CHECKING:
    from jkit.article import Article
    from jkit.user import User


class OwnerInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class CollectionInfo(DataObject, frozen=True):
    id: PositiveInt
    slug: CollectionSlug
    name: NonEmptyStr
    image_url: UserUploadedUrl
    description: str
    description_updated_at: NormalizedDatetime
    new_article_added_at: NormalizedDatetime
    owner_info: OwnerInfoField

    articles_count: NonNegativeInt
    subscribers_count: NonNegativeInt


class ArticleAuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> "User":
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class CollectionArticleInfo(DataObject, frozen=True):
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


class Collection(ResourceObject, CheckableMixin, SlugAndUrlMixin):
    _slug_check_func = is_collection_slug
    _slug_to_url_func = collection_slug_to_url
    _url_to_slug_func = collection_url_to_slug

    def __init__(
        self, *, slug: Optional[str] = None, url: Optional[str] = None
    ) -> None:
        super().__init__()

        self._slug = self._check_params(
            object_readable_name="专题",
            slug=slug,
            url=url,
        )

    async def check(self) -> None:
        if self._checked:
            return

        try:
            await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path=f"/asimov/collections/slug/{self.slug}",
            )
            self._checked = True
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ResourceUnavailableError(
                    f"专题 {self.url} 不存在或已被删除"
                ) from None

            raise

    @property
    async def info(self) -> CollectionInfo:
        await self._auto_check()

        data = await get_json(
            endpoint=CONFIG.endpoints.jianshu,
            path=f"/asimov/collections/slug/{self.slug}",
        )

        return CollectionInfo(
            id=data["id"],
            slug=data["slug"],
            name=data["title"],
            image_url=data["image"],
            description=data["content_in_full"],
            description_updated_at=normalize_datetime(data["last_updated_at"]),
            new_article_added_at=normalize_datetime(data["newly_added_at"]),
            owner_info=OwnerInfoField(
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
        order_by: Literal["add_time", "last_comment_time", "popularity"] = "add_time",
        page_size: int = 20,
    ) -> AsyncGenerator[CollectionArticleInfo, None]:
        await self._auto_check()

        now_page = start_page
        while True:
            data: list[dict[str, Any]] = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path=f"/asimov/collections/slug/{self.slug}/public_notes",
                params={
                    "page": now_page,
                    "count": page_size,
                    "ordered_by": {
                        "add_time": "time",
                        "last_comment_time": "comment_time",
                        "popularity": "hot",
                    }[order_by],
                },
            )  # type: ignore
            if not data:
                return

            for item in data:
                yield CollectionArticleInfo(
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
