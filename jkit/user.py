from __future__ import annotations

from collections.abc import AsyncGenerator
from re import compile as re_compile
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
    NotebookId,
    PositiveInt,
    UserName,
    UserSlug,
    UserUploadedUrl,
)
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_user_slug, is_user_url
from jkit.identifier_convert import user_slug_to_url, user_url_to_slug

if TYPE_CHECKING:
    from jkit.article import Article
    from jkit.collection import Collection
    from jkit.notebook import Notebook

_ASSETS_AMOUNT_REGEX = re_compile(r"收获喜欢[\s\S]*?<p>(.*)</p>[\s\S]*?总资产")

MembershipType = Literal[
    "NONE",
    "BRONZE",
    "SILVER",
    "GOLD",
    "PLATINA",
    "LEGACY_ORDINARY",
    "LEGACY_DISTINGUISHED",
]
GenderType = Literal["UNKNOWN", "MALE", "FEMALE"]


class _BadgeField(DataObject, frozen=True):
    name: NonEmptyStr
    introduction_url: NonEmptyStr
    image_url: NonEmptyStr


class _MembershipInfoField(DataObject, frozen=True):
    type: MembershipType
    expire_time: NormalizedDatetime | None


class InfoData(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    gender: GenderType
    introduction: str
    introduction_update_time: NormalizedDatetime
    avatar_url: UserUploadedUrl
    background_image_url: UserUploadedUrl | None
    badges: tuple[_BadgeField, ...]
    membership_info: _MembershipInfoField
    address_by_ip: NonEmptyStr

    followers_count: NonNegativeInt
    fans_count: NonNegativeInt
    total_wordage: NonNegativeInt
    total_likes_count: NonNegativeInt


class _ArticleAuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class AssetsInfoData(DataObject, frozen=True):
    fp_amount: NonNegativeFloat
    ftn_amount: NonNegativeFloat | None
    assets_amount: NonNegativeFloat | None


class ArticleData(DataObject, frozen=True):
    id: PositiveInt
    slug: ArticleSlug
    title: NonEmptyStr
    description: str
    image_url: UserUploadedUrl | None
    publish_time: NormalizedDatetime
    is_top: bool
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


class NotebookData(DataObject, frozen=True):
    id: NotebookId
    name: NonEmptyStr
    is_serial: bool
    is_paid: bool | None

    def to_notebook_obj(self) -> Notebook:
        from jkit.notebook import Notebook

        return Notebook.from_id(self.id)._as_checked()


class CollectionData(DataObject, frozen=True):
    id: PositiveInt
    slug: CollectionSlug
    name: NonEmptyStr
    image_url: UserUploadedUrl

    def to_collection_obj(self) -> Collection:
        from jkit.collection import Collection

        return Collection.from_slug(self.slug)._as_checked()


class User(ResourceObject, SlugAndUrlResourceMixin, CheckableResourceMixin):
    _resource_readable_name = "用户"

    _slug_check_func = is_user_slug
    _url_check_func = is_user_url

    _url_to_slug_func = user_url_to_slug
    _slug_to_url_func = user_slug_to_url

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
                path=f"/asimov/users/slug/{self.slug}",
                response_type="JSON",
            )
        except HTTPStatusError as e:
            if e.response.status_code == _RESOURCE_UNAVAILABLE_STATUS_CODE:
                raise ResourceUnavailableError(
                    f"用户 {self.url} 不存在或已注销 / 被封禁"
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
            path=f"/asimov/users/slug/{self.slug}",
            response_type="JSON",
        )

        return InfoData(
            id=data["id"],
            slug=data["slug"],
            name=data["nickname"],
            # TODO: 优化类型检查
            gender={
                0: "UNKNOWN",
                1: "MALE",
                2: "FEMALE",
                3: "UNKNOWN",
            }[data["gender"]],  # type: ignore
            introduction=data["intro"],
            introduction_update_time=normalize_datetime(data["last_updated_at"]),
            avatar_url=data["avatar"],
            background_image_url=data["background_image"]
            if data.get("background_image")
            else None,
            badges=tuple(
                _BadgeField(
                    name=badge["text"],
                    introduction_url=badge["intro_url"],
                    image_url=badge["image_url"],
                )
                for badge in data["badges"]
            ),
            membership_info=_MembershipInfoField(
                # TODO: 优化类型检查
                type={
                    "bronze": "BRONZE",
                    "silver": "SILVER",
                    "gold": "GOLD",
                    "platina": "PLATINA",
                    "ordinary": "LEGACY_ORDINARY",
                    "distinguished": "LEGACY_DISTINGUISHED",
                }[data["member"]["type"]],  # type: ignore
                expire_time=normalize_datetime(data["member"]["expires_at"]),
            )
            if data.get("member")
            else _MembershipInfoField(
                type="NONE",
                expire_time=None,
            ),
            address_by_ip=data["user_ip_addr"],
            followers_count=data["following_users_count"],
            fans_count=data["followers_count"],
            total_wordage=data["total_wordage"],
            total_likes_count=data["total_likes_count"],
        )._validate()

    @property
    async def assets_info(self) -> AssetsInfoData:
        fp_amount_data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/asimov/users/slug/{self.slug}",
            response_type="JSON",
        )
        fp_amount = normalize_assets_amount(fp_amount_data["jsd_balance"])

        assets_amount_data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/u/{self.slug}",
            response_type="HTML",
        )
        try:
            assets_amount = float(
                _ASSETS_AMOUNT_REGEX.findall(assets_amount_data)[0]
                .replace(".", "")
                .replace("w", "000")
            )
        except IndexError:
            # 受 API 限制，无法获取此用户的总资产信息
            # 此时简书贝也无法计算
            return AssetsInfoData(
                fp_amount=fp_amount,
                ftn_amount=None,
                assets_amount=None,
            )._validate()
        else:
            ftn_amount = round(assets_amount - fp_amount, 3)
            # 由于总资产信息存在误差（实际值四舍五入，如 10200 -> 10000）
            # 当简书贝数量较少时,如 10100 简书钻 200 简书贝
            # 总资产误差导致数值为 10000，计算结果为 -100 简书贝
            # 此时将总资产增加 500，使计算的简书贝数量为 400
            # 可降低平均误差，并防止简书贝数值为负
            if ftn_amount < 0:
                assets_amount += 500
                ftn_amount = round(assets_amount - fp_amount, 3)

            return AssetsInfoData(
                fp_amount=fp_amount,
                ftn_amount=ftn_amount,
                assets_amount=assets_amount,
            )._validate()

    async def iter_articles(
        self,
        *,
        start_page: int = 1,
        order_by: Literal[
            "PUBLISH_TIME", "LAST_COMMENT_TIME", "POPULARITY"
        ] = "PUBLISH_TIME",
    ) -> AsyncGenerator[ArticleData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/users/slug/{self.slug}/public_notes",
                params={
                    "page": current_page,
                    "count": 20,
                    "order_by": {
                        "PUBLISH_TIME": "shared_at",
                        "LAST_COMMENT_TIME": "commented_at",
                        "POPULARITY": "top",
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
                    is_top=item["is_top"],
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

    async def iter_notebooks(
        self, *, start_page: int = 1
    ) -> AsyncGenerator[NotebookData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/users/{self.slug}/notebooks",
                params={
                    "slug": self.slug,
                    "type": "manager",
                    "page": current_page,
                    "per_page": 20,
                },
                response_type="JSON",
            )
            if not data["notebooks"]:
                return

            for item in data["notebooks"]:
                # TODO: 增加更多字段
                yield NotebookData(
                    id=item["id"],
                    name=item["name"],
                    is_serial=item["book"],
                    is_paid=item.get("paid_book"),
                )._validate()

            current_page += 1

    async def iter_collections(
        self,
        *,
        type: Literal["OWNED", "MANAGED"],
        start_page: int = 1,
    ) -> AsyncGenerator[CollectionData, None]:
        await self._require_check()

        current_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/users/{self.slug}/collections",
                params={
                    "slug": self.slug,
                    "type": {"OWNED": "own", "MANAGED": "manager"}[type],
                    "page": current_page,
                    "per_page": 20,
                },
                response_type="JSON",
            )
            if not data["collections"]:
                return

            for item in data["collections"]:
                yield CollectionData(
                    id=item["id"],
                    slug=item["slug"],
                    name=item["title"],
                    image_url=item["avatar"],
                )._validate()

            current_page += 1
