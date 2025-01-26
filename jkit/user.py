from __future__ import annotations

from collections.abc import AsyncGenerator
from enum import Enum
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
from jkit.exceptions import ResourceUnavailableError
from jkit.identifier_check import is_user_slug, is_user_url
from jkit.identifier_convert import user_slug_to_url, user_url_to_slug
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
    from jkit.collection import Collection
    from jkit.notebook import Notebook

ASSETS_AMOUNT_REGEX = re_compile(r"收获喜欢[\s\S]*?<p>(.*)</p>[\s\S]*?总资产")


class UserBadge(DataObject, frozen=True):
    name: NonEmptyStr
    introduction_url: str
    image_url: NonEmptyStr


class MembershipEnum(Enum):
    NONE = "无会员"
    BRONZE = "铜牌会员"
    SILVER = "银牌会员"
    GOLD = "金牌会员"
    PLATINA = "白金会员"
    LEGACY_ORDINARY = "普通会员（旧版）"
    LEGACY_DISTINGUISHED = "尊享会员（旧版）"


class GenderEnum(Enum):
    UNKNOWN = "未知"
    MALE = "男"
    FEMALE = "女"


class MembershipInfoField(DataObject, frozen=True):
    type: MembershipEnum
    expired_at: NormalizedDatetime | None


class UserInfo(DataObject, frozen=True):
    id: PositiveInt
    name: UserName
    gender: GenderEnum
    introduction: str
    introduction_updated_at: NormalizedDatetime
    avatar_url: UserUploadedUrl
    background_image_url: UserUploadedUrl | None
    badges: tuple[UserBadge, ...]
    membership_info: MembershipInfoField
    address_by_ip: NonEmptyStr

    followers_count: NonNegativeInt
    fans_count: NonNegativeInt
    total_wordage: NonNegativeInt
    total_likes_count: NonNegativeInt
    fp_amount: NonNegativeFloat


class UserCollectionInfo(DataObject, frozen=True):
    id: PositiveInt
    slug: CollectionSlug
    name: NonEmptyStr
    image_url: UserUploadedUrl

    def to_collection_obj(self) -> Collection:
        from jkit.collection import Collection

        return Collection.from_slug(self.slug)._as_checked()


class UserNotebookInfo(DataObject, frozen=True):
    id: PositiveInt
    name: NonEmptyStr
    is_serial: bool
    is_paid: bool | None

    def to_notebook_obj(self) -> Notebook:
        from jkit.notebook import Notebook

        return Notebook.from_id(self.id)


class ArticleAuthorInfoField(DataObject, frozen=True):
    id: PositiveInt
    slug: UserSlug
    name: UserName
    avatar_url: UserUploadedUrl

    def to_user_obj(self) -> User:
        from jkit.user import User

        return User.from_slug(self.slug)._as_checked()


class UserArticleInfo(DataObject, frozen=True):
    id: PositiveInt
    slug: ArticleSlug
    title: NonEmptyStr
    description: str
    image_url: UserUploadedUrl | None
    published_at: NormalizedDatetime
    is_top: bool
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
    async def info(self) -> UserInfo:
        await self._require_check()

        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/asimov/users/slug/{self.slug}",
            response_type="JSON",
        )

        return UserInfo(
            id=data["id"],
            name=data["nickname"],
            gender={
                0: GenderEnum.UNKNOWN,
                1: GenderEnum.MALE,
                2: GenderEnum.FEMALE,
                3: GenderEnum.UNKNOWN,
            }[data["gender"]],
            introduction=data["intro"],
            introduction_updated_at=normalize_datetime(data["last_updated_at"]),
            avatar_url=data["avatar"],
            background_image_url=data["background_image"]
            if data.get("background_image")
            else None,
            badges=tuple(
                UserBadge(
                    name=badge["text"],
                    introduction_url=badge["intro_url"],
                    image_url=badge["image_url"],
                )
                for badge in data["badges"]
            ),
            membership_info=MembershipInfoField(
                type={
                    "bronze": MembershipEnum.BRONZE,
                    "silver": MembershipEnum.SILVER,
                    "gold": MembershipEnum.GOLD,
                    "platina": MembershipEnum.PLATINA,
                    "ordinary": MembershipEnum.LEGACY_ORDINARY,
                    "distinguished": MembershipEnum.LEGACY_DISTINGUISHED,
                }[data["member"]["type"]],
                expired_at=normalize_datetime(data["member"]["expires_at"]),
            )
            if data.get("member")
            else MembershipInfoField(
                type=MembershipEnum.NONE,
                expired_at=None,
            ),
            address_by_ip=data["user_ip_addr"],
            followers_count=data["following_users_count"],
            fans_count=data["followers_count"],
            total_wordage=data["total_wordage"],
            total_likes_count=data["total_likes_count"],
            fp_amount=normalize_assets_amount(data["jsd_balance"]),
        )._validate()

    @property
    async def assets_info(self) -> tuple[float, float | None, float | None]:
        fp_amount = (await self.info).fp_amount

        assets_amount_data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path=f"/u/{self.slug}",
            response_type="HTML",
        )
        try:
            assets_amount = float(
                ASSETS_AMOUNT_REGEX.findall(assets_amount_data)[0]
                .replace(".", "")
                .replace("w", "000")
            )
        except IndexError:
            # 受 API 限制，无法获取此用户的总资产信息
            # 此时简书贝也无法计算
            return (fp_amount, None, None)
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

            return (fp_amount, ftn_amount, assets_amount)

    async def iter_owned_collections(
        self, *, start_page: int = 1, page_size: int = 10
    ) -> AsyncGenerator[UserCollectionInfo, None]:
        await self._require_check()

        now_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/users/{self.slug}/collections",
                body={
                    "slug": self.slug,
                    "type": "own",
                    "page": now_page,
                    "per_page": page_size,
                },
                response_type="JSON",
            )
            if not data["collections"]:
                return

            for item in data["collections"]:
                yield UserCollectionInfo(
                    id=item["id"],
                    slug=item["slug"],
                    name=item["title"],
                    image_url=item["avatar"],
                )._validate()

            now_page += 1

    async def iter_managed_collections(
        self, *, start_page: int = 1, page_size: int = 10
    ) -> AsyncGenerator[UserCollectionInfo, None]:
        await self._require_check()

        now_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/users/{self.slug}/collections",
                body={
                    "slug": self.slug,
                    "type": "manager",
                    "page": now_page,
                    "per_page": page_size,
                },
                response_type="JSON",
            )
            if not data["collections"]:
                return

            for item in data["collections"]:
                yield UserCollectionInfo(
                    id=item["id"],
                    slug=item["slug"],
                    name=item["title"],
                    image_url=item["avatar"],
                )._validate()

            now_page += 1

    async def iter_notebooks(
        self, *, start_page: int = 1, page_size: int = 10
    ) -> AsyncGenerator[UserNotebookInfo, None]:
        await self._require_check()

        now_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/users/{self.slug}/notebooks",
                body={
                    "slug": self.slug,
                    "type": "manager",
                    "page": now_page,
                    "per_page": page_size,
                },
                response_type="JSON",
            )
            if not data["notebooks"]:
                return

            for item in data["notebooks"]:
                yield UserNotebookInfo(
                    id=item["id"],
                    name=item["name"],
                    is_serial=item["book"],
                    is_paid=item.get("paid_book"),
                )._validate()

            now_page += 1

    async def iter_articles(
        self,
        *,
        start_page: int = 1,
        order_by: Literal[
            "PUBLISHED_AT", "LAST_COMMENT_TIME", "POPULARITY"
        ] = "PUBLISHED_AT",
        page_size: int = 10,
    ) -> AsyncGenerator[UserArticleInfo, None]:
        await self._require_check()

        now_page = start_page
        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path=f"/asimov/users/slug/{self.slug}/public_notes",
                body={
                    "page": now_page,
                    "count": page_size,
                    "order_by": {
                        "PUBLISHED_AT": "shared_at",
                        "LAST_COMMENT_TIME": "commented_at",
                        "POPULARITY": "top",
                    }[order_by],
                },
                response_type="JSON_LIST",
            )
            if not data:
                return

            for item in data:
                yield UserArticleInfo(
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
                    is_top=item["object"]["data"]["is_top"],
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
