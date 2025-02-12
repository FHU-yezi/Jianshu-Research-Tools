from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
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
from jkit._normalization import (
    normalize_assets_amount,
    normalize_datetime,
    normalize_percentage,
)
from jkit.constants import (
    _BLANK_LINES_REGEX,
    _HTML_TAG_REGEX,
    _RESOURCE_UNAVAILABLE_STATUS_CODE,
)
from jkit.constraints import (
    ArticleSlug,
    CollectionSlug,
    NonEmptyStr,
    NonNegativeFloat,
    NonNegativeInt,
    NormalizedDatetime,
    NotebookId,
    Percentage,
    PositiveFloat,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_article_slug, is_article_url
from jkit.identifier_convert import article_slug_to_url, article_url_to_slug

if TYPE_CHECKING:
    from jkit.collection import Collection
    from jkit.notebook import Notebook
    from jkit.user import User


PaidType = Literal["FREE", "PAID"]


class _PaidInfoField(DataObject, frozen=True):
    notebook_paid_type: PaidType | None
    article_paid_type: PaidType
    price: PositiveFloat | None
    paid_cotent_percent: Percentage | None
    paid_readers_count: NonNegativeInt | None


class _AuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl
    introduction: str
    address_by_ip: NonEmptyStr

    total_wordage: NonNegativeInt
    total_likes_count: NonNegativeInt

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class InfoData(DataObject, frozen=True):
    id: PositiveInt
    slug: ArticleSlug
    notebook_id: NotebookId
    title: NonEmptyStr
    description: str
    wordage: NonNegativeInt
    published_time: NormalizedDatetime
    updated_time: NormalizedDatetime
    can_comment: bool
    can_reprint: bool
    paid_info: _PaidInfoField
    author_info: _AuthorInfoField
    content_html: NonEmptyStr

    likes_count: NonNegativeInt
    comments_count: NonNegativeInt
    featured_comments_count: NonNegativeInt
    earned_fp_amount: NonNegativeFloat

    @property
    def content_text(self) -> str:
        result = _HTML_TAG_REGEX.sub("", self.content_html)
        return _BLANK_LINES_REGEX.sub("\n", result)


class AudioInfoData(DataObject, frozen=True):
    id: PositiveInt
    name: NonEmptyStr
    producer: NonEmptyStr
    file_url: str  # TODO: 更严格的校验
    duration_seconds: PositiveInt
    file_size_bytes: PositiveInt

    @property
    def file_url_expire_time(self) -> datetime:
        return datetime.fromtimestamp(
            int(self.file_url.split("?")[1].split("&")[0].replace("Expires=", ""))
        )

    @property
    def is_file_url_expired(self) -> bool:
        return self.file_url_expire_time >= datetime.now()


class BelongedNotebookInfoData(DataObject, frozen=True):
    id: PositiveInt
    name: NonEmptyStr

    def to_notebook_obj(self) -> Notebook:
        from jkit.notebook import Notebook

        return Notebook.from_id(self.id)._as_checked()


class IncludedCollectionInfoData(DataObject, frozen=True):
    id: PositiveInt
    slug: CollectionSlug
    # TODO: 优化专题全名获取方式
    name: NonEmptyStr
    image_url: UserUploadedUrl
    owner_name: UserName

    def to_collection_obj(self) -> Collection:
        from jkit.collection import Collection

        return Collection.from_slug(self.slug)._as_checked()

    @property
    async def full_name(self) -> str:
        if "..." not in self.name:
            return self.name

        return (await self.to_collection_obj().info).name


class _CommentPublisherInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl
    address_by_ip: NonEmptyStr

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class SubcommentData(DataObject, frozen=True):
    id: PositiveInt
    # TODO: 解析并转换 @ 其它用户的 HTML 标签
    content: str
    images: tuple[UserUploadedUrl, ...]
    publish_time: NormalizedDatetime
    publisher_info: _CommentPublisherInfoField


class CommentData(SubcommentData, frozen=True):
    floor: PositiveInt
    likes_count: NonNegativeInt

    subcomments: tuple[SubcommentData, ...]

    @property
    def has_subcomment(self) -> bool:
        return bool(self.subcomments)


class FeaturedCommentData(CommentData, frozen=True):
    score: PositiveInt


class Article(ResourceObject, SlugAndUrlResourceMixin, CheckableResourceMixin):
    _resource_readable_name = "文章"

    _slug_check_func = is_article_slug
    _url_check_func = is_article_url

    _url_to_slug_func = article_url_to_slug
    _slug_to_url_func = article_slug_to_url

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
                path=f"/asimov/p/{self.slug}",
                response_type="JSON",
            )
        except HTTPStatusError as e:
            if e.response.status_code == _RESOURCE_UNAVAILABLE_STATUS_CODE:
                raise ResourceUnavailableError(
                    f"文章 {self.url} 不存在或已被删除 / 私密 / 锁定"
                ) from None

            raise
        else:
            self._checked = True

    @property
    async def id(self) -> int:
        return (await self.info).id

    @property
    async def info(self) -> InfoData:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/asimov/p/{self.slug}",
            response_type="JSON",
        )

        return InfoData(
            id=data["id"],
            slug=data["slug"],
            notebook_id=data["notebook_id"],
            title=data["public_title"],
            description=data["description"],
            wordage=data["wordage"],
            published_time=normalize_datetime(data["first_shared_at"]),
            updated_time=normalize_datetime(data["last_updated_at"]),
            can_comment=data["commentable"],
            can_reprint=data["reprintable"],
            paid_info=_PaidInfoField(
                notebook_paid_type={
                    "free": None,  # 免费文章
                    "fbook_free": "FREE",  # 免费连载中的免费文章
                    "pbook_free": "PAID",  # 付费连载中的免费文章
                    "paid": None,  # 付费文章
                    "fbook_paid": "FREE",  # 免费连载中的付费文章
                    "pbook_paid": "PAID",  # 付费连载中的付费文章
                }[data["paid_type"]],
                # TODO: 优化类型检查
                article_paid_type={
                    "free": "FREE",  # 免费文章
                    "fbook_free": "FREE",  # 免费连载中的免费文章
                    "pbook_free": "FREE",  # 付费连载中的免费文章
                    "paid": "PAID",  # 付费文章
                    "fbook_paid": "PAID",  # 免费连载中的付费文章
                    "pbook_paid": "PAID",  # 付费连载中的付费文章
                }[data["paid_type"]],  # type: ignore
                price=float(data["retail_price"]) / 100
                if data.get("retail_price")
                else None,
                paid_cotent_percent=normalize_percentage(
                    float(data["paid_content_percent"].replace("%", ""))
                )
                if data.get("paid_content_percent")
                else None,
                paid_readers_count=data.get("purchased_count"),
            ),
            author_info=_AuthorInfoField(
                id=data["user"]["id"],
                slug=data["user"]["slug"],
                name=data["user"]["nickname"],
                avatar_url=data["user"]["avatar"],
                introduction=data["user"]["intro"],
                address_by_ip=data["user"]["user_ip_addr"],
                total_wordage=data["user"]["wordage"],
                total_likes_count=data["user"]["likes_count"],
            ),
            content_html=data["free_content"],
            likes_count=data["likes_count"],
            comments_count=data["public_comment_count"],
            featured_comments_count=data["featured_comments_count"],
            earned_fp_amount=normalize_assets_amount(data["total_fp_amount"]),
        )._validate()

    @property
    async def views_count(self) -> int:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/shakespeare/v2/notes/{self.slug}/views_count",
            response_type="JSON",
        )

        return data["views_count"]

    @property
    async def audio_info(self) -> AudioInfoData | None:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/shakespeare/v2/notes/{self.slug}/audio",
            response_type="JSON",
        )

        if not data["exists"]:
            return None

        return AudioInfoData(
            id=data["id"],
            name=data["title"],
            producer=data["dubber"],
            file_url=data["play_url"],
            duration_seconds=data["duration"],
            file_size_bytes=data["filesize"],
        )._validate()

    @property
    async def belonged_notebook_info(self) -> BelongedNotebookInfoData:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/shakespeare/v2/notes/{self.slug}/book",
            response_type="JSON",
        )

        return BelongedNotebookInfoData(
            id=data["notebook_id"],
            name=data["notebook_name"],
        )._validate()

    async def iter_included_collections(
        self, *, start_page: int = 1
    ) -> AsyncGenerator[IncludedCollectionInfoData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/shakespeare/notes/{await self.id}/included_collections",
                params={"page": current_page, "count": 20},
                response_type="JSON",
            )
            if not data["collections"]:
                return

            for item in data["collections"]:
                yield IncludedCollectionInfoData(
                    id=item["id"],
                    slug=item["slug"],
                    name=item["title"],
                    image_url=item["avatar"],
                    owner_name=item["owner_name"],
                )._validate()

            current_page += 1

    async def iter_comments(
        self,
        *,
        start_page: int = 1,
        direction: Literal["ASC", "DESC"] = "DESC",
        author_only: bool = False,
    ) -> AsyncGenerator[CommentData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/shakespeare/notes/{await self.id}/comments",
                params={
                    "page": current_page,
                    "order_by": direction.lower(),
                    "author_only": author_only,
                    "count": 20,
                },
                response_type="JSON",
            )
            if not data["comments"]:
                return

            for item in data["comments"]:
                yield CommentData(
                    id=item["id"],
                    floor=item["floor"],
                    content=item["compiled_content"],
                    images=tuple(image["url"] for image in item["images"])
                    if item["images"]
                    else (),
                    likes_count=item["likes_count"],
                    publish_time=normalize_datetime(item["created_at"]),
                    publisher_info=_CommentPublisherInfoField(
                        id=item["user"]["id"],
                        slug=item["user"]["slug"],
                        name=item["user"]["nickname"],
                        avatar_url=item["user"]["avatar"],
                        address_by_ip=item["user"]["user_ip_addr"],
                    ),
                    subcomments=tuple(
                        SubcommentData(
                            id=subcomment["id"],
                            content=subcomment["compiled_content"],
                            images=tuple(image["url"] for image in subcomment["images"])
                            if subcomment["images"]
                            else (),
                            publish_time=normalize_datetime(subcomment["created_at"]),
                            publisher_info=_CommentPublisherInfoField(
                                id=subcomment["user"]["id"],
                                slug=subcomment["user"]["slug"],
                                name=subcomment["user"]["nickname"],
                                avatar_url=subcomment["user"]["avatar"],
                                address_by_ip=subcomment["user"]["user_ip_addr"],
                            ),
                        )
                        for subcomment in item["children"]
                    ),
                )._validate()

            current_page += 1

    async def iter_featured_comments(
        self,
        *,
        count: int = 10,
    ) -> AsyncGenerator[FeaturedCommentData, None]:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/shakespeare/notes/{self.slug}/featured_comments",
            params={
                "count": count,
            },
            response_type="JSON_LIST",
        )

        for item in data:
            yield FeaturedCommentData(
                id=item["id"],
                floor=item["floor"],
                content=item["compiled_content"],
                images=tuple(image["url"] for image in item["images"])
                if item["images"]
                else (),
                likes_count=item["likes_count"],
                publish_time=normalize_datetime(item["created_at"]),
                publisher_info=_CommentPublisherInfoField(
                    id=item["user"]["id"],
                    slug=item["user"]["slug"],
                    name=item["user"]["nickname"],
                    avatar_url=item["user"]["avatar"],
                    address_by_ip=item["user"]["user_ip_addr"],
                ),
                subcomments=tuple(
                    SubcommentData(
                        id=subcomment["id"],
                        content=subcomment["compiled_content"],
                        images=tuple(image["url"] for image in subcomment["images"])
                        if subcomment["images"]
                        else (),
                        publish_time=normalize_datetime(subcomment["created_at"]),
                        publisher_info=_CommentPublisherInfoField(
                            id=subcomment["user"]["id"],
                            slug=subcomment["user"]["slug"],
                            name=subcomment["user"]["nickname"],
                            avatar_url=subcomment["user"]["avatar"],
                            address_by_ip=subcomment["user"]["user_ip_addr"],
                        ),
                    )
                    for subcomment in item["children"]
                ),
                score=item["score"],
            )._validate()
