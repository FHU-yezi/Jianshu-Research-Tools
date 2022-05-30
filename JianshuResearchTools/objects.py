from datetime import datetime
from typing import Dict, List

from . import article, collection, island, notebook, user
from .assert_funcs import (AssertArticleUrl, AssertCollectionUrl,
                           AssertIslandUrl, AssertNotebookUrl, AssertUserUrl)
from .convert import (ArticleSlugToArticleUrl, CollectionSlugToCollectionUrl,
                      IslandSlugToIslandUrl, IslandUrlToIslandSlug,
                      NotebookSlugToNotebookUrl, UserSlugToUserUrl,
                      UserUrlToUserSlug)
from .exceptions import InputError
from .utils import CallWithoutCheck, NameValueMappingToString

__all__ = [
    "DISABLE_CACHE", "User", "Article", "Notebook", "Collection", "Island"
]

DISABLE_CACHE = False  # 禁用缓存


def cache_result(func):
    """缓存函数的返回值"""
    cache_Dict = {}

    def wrapper(*args, **kwargs):
        args_hash = hash((hash(args[0]),) + tuple(args[1:]) + tuple(kwargs.items()))
        cache_result = cache_Dict.get(args_hash)
        if cache_result and not DISABLE_CACHE:
            return cache_result
        else:
            result = func(*args, **kwargs)
            if not DISABLE_CACHE:
                cache_Dict[args_hash] = result
            return result
    return wrapper


class User():
    """用户类
    """
    def __init__(self, user_url: str = None, *, user_slug: str = None):
        """构建新的用户对象

        Args:
            user_url (str, optional): 用户个人主页 URL. Defaults to None.
            user_slug (str, optional): 用户 Slug. Defaults to None.
        """
        # TODO: 支持使用用户 Id 初始化用户对象
        if user_slug and user_url:
            raise InputError("只能使用一个参数进行用户类的初始化")
        elif user_url:
            AssertUserUrl(user_url)
            self._url = user_url
        elif user_slug:
            user_url = UserSlugToUserUrl(user_slug)
            AssertUserUrl(user_url)
            self._url = user_url
        else:
            raise InputError("请至少传入一个参数")

    @property
    def url(self) -> str:
        """获取用户主页 URL

        Returns:
            str: 用户主页 URL
        """
        return self._url

    @property
    @cache_result
    def slug(self) -> str:
        """获取用户 Slug

        Returns:
            str: 用户 Slug
        """
        return UserUrlToUserSlug(self._url)

    @property
    @cache_result
    def name(self) -> str:
        """获取用户昵称

        Returns:
            str: 用户昵称
        """
        return CallWithoutCheck(user.GetUserName, self._url)

    @property
    @cache_result
    def gender(self) -> int:
        """获取用户性别

        Returns:
            int: 用户性别，0 为未知，1 为男，2 为女
        """
        return CallWithoutCheck(user.GetUserGender, self._url)

    @property
    @cache_result
    def followers_count(self) -> int:
        """获取用户关注数

        Returns:
            int: 关注数
        """
        return CallWithoutCheck(user.GetUserFollowersCount, self._url)

    @property
    @cache_result
    def fans_count(self) -> int:
        """获取用户粉丝数

        Returns:
            int: 粉丝数
        """
        return CallWithoutCheck(user.GetUserFansCount, self._url)

    @property
    @cache_result
    def articles_count(self) -> int:
        """获取用户文章数

        Returns:
            int: 文章数
        """
        return CallWithoutCheck(user.GetUserArticlesCount, self._url)

    @property
    @cache_result
    def wordage(self) -> int:
        """获取用户总字数

        Returns:
            int: 总字数
        """
        return CallWithoutCheck(user.GetUserWordage, self._url)

    @property
    @cache_result
    def likes_count(self) -> int:
        """获取用户被点赞数

        Returns:
            int: 被点赞数
        """
        return CallWithoutCheck(user.GetUserLikesCount, self._url)

    @property
    @cache_result
    def assets_count(self) -> float:
        """获取用户资产量

        Returns:
            int: 资产量
        """
        return CallWithoutCheck(user.GetUserAssetsCount, self._url)

    @property
    @cache_result
    def FP_count(self) -> float:
        """获取用户简书钻数量

        Returns:
            int: 简书钻数量
        """
        return CallWithoutCheck(user.GetUserFPCount, self._url)

    @property
    @cache_result
    def FTN_count(self) -> float:
        """获取用户简书贝数量

        Returns:
            int: 简书贝数量
        """
        return CallWithoutCheck(user.GetUserFTNCount, self._url)

    @property
    @cache_result
    def badges(self) -> List:
        """获取徽章列表

        Returns:
            List: 徽章列表
        """
        return CallWithoutCheck(user.GetUserBadgesList, self._url)

    @property
    @cache_result
    def last_update_time(self) -> datetime:
        """获取最近更新时间

        Returns:
            datetime: 最近更新时间
        """
        return CallWithoutCheck(user.GetUserLastUpdateTime, self._url)

    @property
    @cache_result
    def VIP_info(self) -> Dict:
        """获取用户会员信息

        Returns:
            Dict: 会员信息
        """
        return CallWithoutCheck(user.GetUserVIPInfo, self._url)

    @property
    @cache_result
    def introduction_text(self) -> str:
        """获取纯文本格式的用户简介

        Returns:
            str: 纯文本格式的用户简介
        """
        return CallWithoutCheck(user.GetUserIntroductionText, self._url)

    @property
    @cache_result
    def introduction_html(self) -> str:
        """获取 Html 格式的用户简介

        Returns:
            str: Html 格式的用户简介
        """
        return CallWithoutCheck(user.GetUserIntroductionHtml, self._url)

    @property
    @cache_result
    def notebooks(self) -> List:
        """获取用户文集信息

        Returns:
            List: 文集信息
        """
        return CallWithoutCheck(user.GetUserNotebooksInfo, self._url)

    @property
    @cache_result
    def own_collections(self) -> List:
        """获取自己创建的专题信息

        Returns:
            List: 自己创建的专题信息
        """
        return CallWithoutCheck(user.GetUserOwnCollectionsInfo, self._url)

    @property
    @cache_result
    def manageable_collections(self) -> List:
        """获取用户有管理权的专题信息

        Returns:
            List: 有管理权的专题信息
        """
        return CallWithoutCheck(user.GetUserManageableCollectionsInfo, self._url)

    @cache_result
    def articles_info(self, page: int = 1, count: int = 10) -> List[Dict]:
        """获取文章信息

        Args:
            page (int, optional): 页码. Defaults to 1.
            count (int, optional): 每次获取的文章信息数量. Defaults to 1.

        Returns:
            List[Dict]: 文章信息
        """
        return CallWithoutCheck(user.GetUserArticlesInfo, self._url, page, count)

    @cache_result
    def following_info(self, page: int = 1) -> List[Dict]:
        """获取关注者信息

        Args:
            page (int, optional): 页码. Defaults to 1.

        Returns:
            List[Dict]: 关注者信息
        """
        return CallWithoutCheck(user.GetUserFollowingInfo, self._url, page)

    @cache_result
    def fans_info(self, page: int = 1) -> List[Dict]:
        """获取粉丝信息

        Args:
            page (int, optional): 页码. Defaults to 1.

        Returns:
            List[Dict]: 粉丝信息
        """
        return CallWithoutCheck(user.GetUserFansInfo, self._url, page)

    def __eq__(self, other: object) -> bool:
        """判断是否是同一个用户

        Args:
            other (object): 另一个对象

        Returns:
            bool: 判断结果
        """
        if not isinstance(other, User):
            return False  # 不是由用户类构建的必定不相等
        if self._url == other._url:
            return True
        else:
            return False

    def __hash__(self) -> int:
        """返回基于用户 URL 的哈希值

        Returns:
            int: 哈希值
        """
        return hash(self._url)

    def __str__(self) -> str:
        """输出用户信息摘要

        Returns:
            str: 用户信息摘要
        """
        return NameValueMappingToString({
            "昵称": (self.name, False),
            "URL": (self.url, False),
            "性别": (self.gender, False),
            "关注者数": (self.followers_count, False),
            "粉丝数": (self.fans_count, False),
            "文章数": (self.articles_count, False),
            "总字数": (self.wordage, False),
            "简书钻": (self.FP_count, False),
            "简书贝": (self.FTN_count, False),
            "总资产": (self.assets_count, False),
            "徽章": (' '.join(self.badges), False),
            "最后更新时间": (self.last_update_time, False),
            "会员等级": (self.VIP_info["vip_type"], False),
            "会员过期时间": (self.VIP_info["expire_date"], False),
            "个人简介": (self.introduction_text, True)
        }, title="用户信息摘要")


class Article():
    """文章类
    """
    def __init__(self, article_url: str = None, article_slug: str = None):
        """构建新的文章对象

        Args:
            article_url (str, optional): 文章 URL. Defaults to None.
            article_slug (str, optional): 文章 Slug. Defaults to None.
        """
        # TODO: 支持使用文章 Id 初始化文章对象
        if article_slug and article_url:
            raise InputError("只能使用一个参数进行文章类的初始化")
        elif article_url:
            AssertArticleUrl(article_url)
            self._url = article_url
        elif article_slug:
            article_url = ArticleSlugToArticleUrl(article_slug)
            AssertArticleUrl(article_url)
            self._url = article_url
        else:
            raise InputError("请至少传入一个参数")

    @property
    def url(self) -> str:
        """获取文章 URL

        Returns:
            str: 文章 URL
        """
        return self._url

    @property
    @cache_result
    def slug(self) -> str:
        """获取文章 Slug

        Returns:
            str: 文章 Slug
        """
        return article.GetArticleSlug(self._url)

    @property
    @cache_result
    def title(self) -> str:
        """获取文章标题

        Returns:
            str: 标题
        """
        return CallWithoutCheck(article.GetArticleTitle, self._url)

    @property
    @cache_result
    def author_name(self) -> str:
        """获取文章作者名

        Returns:
            str: 作者名
        """
        return CallWithoutCheck(article.GetArticleAuthorName, self._url)

    @property
    @cache_result
    def wordage(self) -> int:
        """获取文章总字数

        Returns:
            int: 总字数
        """
        return CallWithoutCheck(article.GetArticleWordage, self._url)

    @property
    @cache_result
    def reads_count(self) -> int:
        """获取文章阅读量

        Returns:
            int: 阅读量
        """
        return CallWithoutCheck(article.GetArticleReadsCount, self._url)

    @property
    @cache_result
    def likes_count(self) -> int:
        """获取文章点赞量

        Returns:
            int: 文章点赞量
        """
        return CallWithoutCheck(article.GetArticleLikesCount, self._url)

    @property
    @cache_result
    def comments_count(self) -> int:
        """获取文章评论量

        Returns:
            int: 文章评论量
        """
        return CallWithoutCheck(article.GetArticleCommentsCount, self._url)

    @property
    @cache_result
    def most_valuable_comments_count(self) -> int:
        """获取文章精选评论量

        Returns:
            int: 文章精选评论量
        """
        return CallWithoutCheck(article.GetArticleMostValuableCommentsCount, self._url)

    @property
    @cache_result
    def total_FP_count(self) -> float:
        """获取文章总获钻量

        Returns:
            int: 文章总获钻量
        """
        return CallWithoutCheck(article.GetArticleTotalFPCount, self._url)

    @property
    @cache_result
    def description(self) -> str:
        """获取文章摘要

        Returns:
            str: 文章摘要
        """
        return CallWithoutCheck(article.GetArticleDescription, self._url)

    @property
    @cache_result
    def publish_time(self) -> datetime:
        """获取文章发布时间

        Returns:
            datetime: 文章发布时间
        """
        return CallWithoutCheck(article.GetArticlePublishTime, self._url)

    @property
    @cache_result
    def update_time(self) -> datetime:
        """获取文章更新时间

        Returns:
            datetime: 文章更新时间
        """
        return CallWithoutCheck(article.GetArticleUpdateTime, self._url)

    @property
    @cache_result
    def paid_status(self) -> bool:
        """获取文章付费状态

        Returns:
            bool: 文章付费状态
        """
        return CallWithoutCheck(article.GetArticlePaidStatus, self._url)

    @property
    @cache_result
    def reprint_status(self) -> bool:
        """获取文章转载状态

        Returns:
            bool: 文章转载状态
        """
        return CallWithoutCheck(article.GetArticleReprintStatus, self._url)

    @property
    @cache_result
    def comment_status(self) -> bool:
        """获取文章评论状态

        Returns:
            bool: 文章评论状态
        """
        return CallWithoutCheck(article.GetArticleCommentStatus, self._url)

    @property
    @cache_result
    def html(self) -> str:
        """获取 Html 格式的文章内容

        # ! 该函数可以获取设置禁止转载的文章内容，请尊重作者版权，由此带来的风险您需自行承担
        # ! 该函数不能获取文章付费部分的内容

        Returns:
            str: Html 格式的文章内容
        """
        return CallWithoutCheck(article.GetArticleHtml, self._url)

    @property
    @cache_result
    def text(self) -> str:
        """获取纯文本格式的文章内容

        # ! 该函数可以获取设置禁止转载的文章内容，请尊重作者版权，由此带来的风险您需自行承担
        # ! 该函数不能获取文章付费部分的内容

        Returns:
            str: 纯文本格式的文章内容
        """
        return CallWithoutCheck(article.GetArticleText, self._url)

    @property
    @cache_result
    def markdown(self) -> str:
        """获取 Markdown 格式的文章内容

        # ! 该函数可以获取设置禁止转载的文章内容，请尊重作者版权，由此带来的风险您需自行承担
        # ! 该函数不能获取文章付费部分的内容

        Returns:
            str: Markdown 格式的文章内容
        """
        return CallWithoutCheck(article.GetArticleMarkdown, self._url)

    def __eq__(self, other: object) -> bool:
        """判断是否是同一篇文章

        Args:
            other (object): 另一个对象

        Returns:
            bool: 判断结果
        """
        if not isinstance(other, Article):
            return False  # 不是由文章类构建的必定不相等
        if self._url == other._url:
            return True
        else:
            return False

    def __hash__(self) -> int:
        """返回基于文章 URL 的哈希值

        Returns:
            int: 哈希值
        """
        return hash(self._url)

    def __str__(self) -> str:
        """输出文章信息摘要

        Returns:
            str: 文章信息摘要
        """
        return NameValueMappingToString({
            "标题": (self.title, False),
            "URL": (self.url, False),
            "作者名": (self.author_name, False),
            "字数": (self.wordage, False),
            "阅读量": (self.reads_count, False),
            "点赞数": (self.likes_count, False),
            "评论数": (self.comments_count, False),
            "精选评论数": (self.most_valuable_comments_count, False),
            "总获钻量": (self.total_FP_count, False),
            "发布时间": (self.publish_time, False),
            "更新时间": (self.update_time, False),
            "需付费": (self.paid_status, False),
            "可转载": (self.reprint_status, False),
            "可评论": (self.comment_status, False),
            "摘要": (self.description, True)
        }, title="文章信息摘要")


class Notebook():
    """文集类
    """
    def __init__(self, notebook_url: str = None, notebook_slug: str = None):
        """构建新的文集对象

        Args:
            notebook_url (str, optional): 文集 URL. Defaults to None.
            notebook_slug (str, optional): 文集 Slug. Defaults to None.
        """
        # TODO: 支持使用用户 Id 初始化用户对象
        if notebook_slug and notebook_url:
            raise InputError("只能使用一个参数进行文集类的初始化")
        elif notebook_url:
            AssertNotebookUrl(notebook_url)
            self._url = notebook_url
        elif notebook_slug:
            notebook_url = NotebookSlugToNotebookUrl(notebook_slug)
            AssertNotebookUrl(notebook_url)
            self._url = notebook_url
        else:
            raise InputError("请至少传入一个参数")

    @property
    def url(self) -> str:
        """获取文集 URL

        Returns:
            str: 文集 URL
        """
        return self._url

    @property
    @cache_result
    def id(self) -> int:
        """获取文集 ID

        Returns:
            int: 文集 ID
        """
        return notebook.GetNotebookId(self._url)

    @property
    @cache_result
    def slug(self) -> str:
        """获取文集 Slug

        Returns:
            str: 文集 Slug
        """
        return notebook.GetNotebookSlug(self._url)

    @property
    @cache_result
    def name(self) -> str:
        """获取文集名称

        Returns:
            str: 文集名称
        """
        return CallWithoutCheck(notebook.GetNotebookName, self._url)

    @property
    @cache_result
    def articles_count(self) -> int:
        """获取文集中的文章总数

        Returns:
            int: 文章总数
        """
        return CallWithoutCheck(notebook.GetNotebookArticlesCount, self._url)

    @property
    @cache_result
    def author_name(self) -> str:
        """获取文集的作者名

        Returns:
            str: 作者名
        """
        return CallWithoutCheck(notebook.GetNotebookAuthorInfo, self._url)["name"]

    @property
    @cache_result
    def author_info(self) -> Dict:
        """获取文集的作者信息

        Returns:
            Dict: 作者信息
        """
        return CallWithoutCheck(notebook.GetNotebookAuthorInfo, self._url)

    @property
    @cache_result
    def wordage(self) -> int:
        """获取文集中所有文章的总字数

        Returns:
            int: 文集总字数
        """
        return CallWithoutCheck(notebook.GetNotebookWordage, self._url)

    @property
    @cache_result
    def subscribers_count(self) -> int:
        """获取文集的关注者数量

        Returns:
            int: 关注者数量
        """
        return CallWithoutCheck(notebook.GetNotebookSubscribersCount, self._url)

    @property
    @cache_result
    def update_time(self) -> datetime:
        """获取文集的更新时间

        Returns:
            datetime: 更新时间
        """
        return CallWithoutCheck(notebook.GetNotebookUpdateTime, self._url)

    @cache_result
    def articles_info(self, page: int = 1, count: int = 10, sorting_method: str = "time") -> List[Dict]:
        """获取文集中的文章信息

        Args:
            page (int, optional): 页码. Defaults to 1.
            count (int, optional): 每次返回的数据数量. Defaults to 10.
            sorting_method (str, optional): 排序方法，time 为按照发布时间排序，
            comment_time 为按照最近评论时间排序，hot 为按照热度排序. Defaults to "time".

        Returns:
            List[Dict]: 文章信息
        """
        return CallWithoutCheck(notebook.GetNotebookArticlesInfo, self._url, page, count, sorting_method)

    def __eq__(self, other: object) -> bool:
        """判断是否是同一个文集

        Args:
            other (object): 另一个对象

        Returns:
            bool: 判断结果
        """
        if not isinstance(other, Notebook):
            return False  # 不是由文集类构建的必定不相等
        if self._url == other._url:
            return True
        else:
            return False

    def __hash__(self) -> int:
        """返回基于文集 URL 的哈希值

        Returns:
            int: 哈希值
        """
        return hash(self._url)

    def __str__(self) -> str:
        """输出文集信息摘要

        Returns:
            str: 文集信息摘要
        """
        return NameValueMappingToString({
            "名称": (self.name, False),
            "URL": (self.url, False),
            "作者名": (self.author_name, False),
            "文章数": (self.articles_count, False),
            "总字数": (self.wordage, False),
            "关注者数": (self.subscribers_count, False),
            "更新时间": (self.update_time, False)
        }, title="文集信息摘要")


class Collection():
    """专题类
    """
    def __init__(self, collection_url: str = None, collection_slug: str = None,
                 collection_id: int = None):
        """初始化专题类

        Args:
            collection_url (str, optional): 专题 URL. Defaults to None.
            collection_slug (str, optional): 专题 Slug. Defaults to None.
            collection_id (int, optional): 专题 Id，如不传入部分数据将无法获取. Defaults to None.
        """
        # TODO: 支持通过 collection_url 获取 collection_id
        if collection_slug and collection_url:
            raise InputError("只能使用一个参数进行专题类的初始化")
        elif collection_url:
            AssertCollectionUrl(collection_url)
            self._url = collection_url
        elif collection_slug:
            collection_url = CollectionSlugToCollectionUrl(collection_slug)
            AssertCollectionUrl(collection_url)
            self._url = collection_url
        else:
            raise InputError("请至少传入一个参数")

        if collection_id:
            self._id = collection_id
        else:
            self._id = None

    @property
    def url(self) -> str:
        """获取专题 URL

        Returns:
            str: 专题 URL
        """
        return self._url

    @property
    @cache_result
    def slug(self) -> str:
        """获取专题 Slug

        Returns:
            str: 专题 Slug
        """
        return collection.GetCollectionSlug(self._url)

    @property
    @cache_result
    def name(self) -> str:
        """获取专题名称

        Returns:
            str: 专题名称
        """
        return CallWithoutCheck(collection.GetCollectionName, self._url)

    @property
    @cache_result
    def avatar_url(self) -> str:
        """获取专题头像链接

        Returns:
            str: 专题头像链接
        """
        return CallWithoutCheck(collection.GetCollectionAvatarUrl, self._url)

    @property
    @cache_result
    def introduction_text(self) -> str:
        """获取纯文本格式的专题简介

        Returns:
            str: 纯文本格式的专题简介
        """
        return CallWithoutCheck(collection.GetCollectionIntroductionText, self._url)

    @property
    @cache_result
    def introduction_html(self) -> str:
        """获取 Html 格式的专题简介

        Returns:
            str:  Html 格式的专题简介
        """
        return CallWithoutCheck(collection.GetCollectionIntroductionHtml, self._url)

    @property
    @cache_result
    def articles_update_time(self) -> datetime:
        """获取专题文章更新时间

        Returns:
            datetime: 专题文章更新时间
        """
        return CallWithoutCheck(collection.GetCollectionArticlesUpdateTime, self._url)

    @property
    @cache_result
    def info_update_time(self) -> datetime:
        """获取专题信息更新时间

        Returns:
            datetime: 专题信息更新时间
        """
        return CallWithoutCheck(collection.GetCollectionInformationUpdateTime, self._url)

    @property
    @cache_result
    def owner_info(self) -> Dict:
        """获取专题的所有者信息

        Returns:
            Dict: 用户信息
        """
        return CallWithoutCheck(collection.GetCollectionOwnerInfo, self._url)

    @property
    @cache_result
    def articles_count(self) -> int:
        """获取专题文章数

        Returns:
            int: 专题文章数
        """
        return CallWithoutCheck(collection.GetCollectionArticlesCount, self._url)

    @property
    @cache_result
    def subscribers_count(self) -> int:
        """获取专题关注者数

        Returns:
            int: 专题关注者数
        """
        return CallWithoutCheck(collection.GetCollectionSubscribersCount, self._url)

    @cache_result
    def editors_info(self, page: int = 1) -> List[Dict]:
        """获取专题编辑信息

        Args:
            page (int, optional): 页码. Defause to 1.

        Raises:
            InputError: 因缺少 ID 参数而无法获取结果时抛出此异常

        Returns:
            List[Dict]: 编辑信息
        """
        if not self._id:
            raise InputError("实例化该专题对象时未传入 ID 参数，无法获取编辑信息")
        return CallWithoutCheck(collection.GetCollectionEditorsInfo, self._id, page)

    @cache_result
    def recommended_writers_info(self, page: int = False) -> List[Dict]:
        """获取专题推荐作者信息

        Args:
            page (int, optional): 页码. Defaults to False.

        Raises:
            InputError: 因缺少 ID 参数而无法获取结果时抛出此异常

        Returns:
            List[Dict]: 推荐作者信息
        """
        if not self._id:
            raise InputError("实例化该专题对象时未传入 ID 参数，无法获取推荐作者信息")
        return CallWithoutCheck(collection.GetCollectionRecommendedWritersInfo, self._id, page)

    @cache_result
    def subscribers_info(self, start_sort_id: int) -> List:
        """获取专题关注者信息

        Args:
            start_sort_id (int): 起始序号，等于上一条数据的序号

        Raises:
            InputError: 因缺少 ID 参数而无法获取结果时抛出此异常

        Returns:
            List: 关注者信息
        """
        if not self._id:
            raise InputError("实例化该专题对象时未传入 ID 参数，无法获取关注者信息")
        return CallWithoutCheck(collection.GetCollectionSubscribersInfo, self._id, start_sort_id)

    @cache_result
    def articles_info(self, page: int = 1, count: int = 10,
                      sorting_method: str = "time") -> List[Dict]:
        """获取专题文章信息

        Args:
            page (int, optional): 页码. Defaults to 1.
            count (int, optional): 每次返回的数据数量. Defaults to 10.
            sorting_method (str, optional): 排序方法，time 为按照发布时间排序，
            comment_time 为按照最近评论时间排序，hot 为按照热度排序. Defaults to "time".

        Returns:
            List[Dict]: 专题中的文章信息
        """
        return CallWithoutCheck(collection.GetCollectionArticlesInfo, self._url, page, count, sorting_method)

    def __eq__(self, other: object) -> bool:
        """判断是否是同一个专题

        Args:
            other (object): 另一个对象

        Returns:
            bool: 判断结果
        """
        if not isinstance(other, Collection):
            return False  # 不是由专题类构建的必定不相等
        if self._url == other._url:
            return True
        else:
            return False

    def __hash__(self) -> int:
        """返回基于专题 URL 的哈希值

        Returns:
            int: 哈希值
        """
        return hash(self._url)

    def __str__(self) -> str:
        """输出专题信息摘要

        Returns:
            str: 专题信息摘要
        """
        return NameValueMappingToString({
            "专题名": (self.name, False),
            "URL": (self.url, False),
            "主编名": (self.owner_info["name"], False),
            "图片链接": (self.avatar_url, False),
            "文章数": (self.articles_count, False),
            "关注者数": (self.subscribers_count, False),
            "文章更新时间": (self.articles_update_time, False),
            "信息更新时间": (self.info_update_time, False),
            "简介": (self.introduction_text, True),
        }, title="专题信息摘要")


class Island():
    """小岛类
    """
    def __init__(self, island_url: str = None, island_slug: str = None):
        if island_slug and island_url:
            raise InputError("只能使用一个参数进行小岛类的初始化")
        elif island_url:
            AssertIslandUrl(island_url)
            self._url = island_url
        elif island_slug:
            island_url = IslandSlugToIslandUrl(island_slug)
            AssertIslandUrl(island_url)
            self._url = island_url
        else:
            raise InputError("请至少传入一个参数")

    @property
    def url(self) -> str:
        """获取小岛 URL

        Returns:
            str: 小岛 URL
        """
        return self._url

    @property
    @cache_result
    def slug(self) -> str:
        """获取小岛 Slug

        Returns:
            str: 小岛 Slug
        """
        return IslandUrlToIslandSlug(self._url)

    @property
    @cache_result
    def name(self) -> str:
        """获取小岛名称

        Returns:
            str: 小岛名称
        """
        return CallWithoutCheck(island.GetIslandName, self._url)

    @property
    @cache_result
    def avatar_url(self) -> str:
        """获取小岛头像链接

        Returns:
            str: 小岛头像链接
        """
        return CallWithoutCheck(island.GetIslandAvatarUrl, self._url)

    @property
    @cache_result
    def introduction(self) -> str:
        """获取小岛简介

        Returns:
            str: 小岛简介
        """
        return CallWithoutCheck(island.GetIslandIntroduction, self._url)

    @property
    @cache_result
    def members_count(self) -> int:
        """获取小岛成员数量

        Returns:
            int: 成员数量
        """
        return CallWithoutCheck(island.GetIslandMembersCount, self._url)

    @property
    @cache_result
    def posts_count(self) -> int:
        """获取小岛帖子数量

        Returns:
            int: 帖子数量
        """
        return CallWithoutCheck(island.GetIslandPostsCount, self._url)

    @property
    @cache_result
    def category(self) -> str:
        """获取小岛分类

        Returns:
            str: 分类
        """
        return CallWithoutCheck(island.GetIslandCategory, self._url)

    @cache_result
    def posts(self, start_sort_id: int = None, count: int = 10,
              topic_id: int = None, sorting_method: str = "time") -> List[Dict]:
        """获取小岛帖子信息

        Args:
            start_sort_id (int, optional): 起始序号，等于上一条数据的序号. Defaults to None.
            count (int, optional): 每次返回的数据数量. Defaults to 10.
            topic_id (int, optional): 话题 ID. Defaults to None.
            sorting_method (str, optional): 排序方法，time 为按照发布时间排序，
            comment_time 为按照最近评论时间排序，hot 为按照热度排序. Defaults to "time".

        Returns:
            List[Dict]: 帖子信息
        """
        return CallWithoutCheck(island.GetIslandPosts, self._url, start_sort_id, count, topic_id, sorting_method)

    def __eq__(self, other: object) -> bool:
        """判断是否是同一个小岛

        Args:
            other (object): 另一个对象

        Returns:
            bool: 判断结果
        """
        if not isinstance(other, Collection):
            return False  # 不是由小岛类构建的必定不相等
        if self._url == other._url:
            return True
        else:
            return False

    def __hash__(self) -> int:
        """返回基于小岛 URL 的哈希值

        Returns:
            int: 哈希值
        """
        return hash(self._url)

    def __str__(self) -> str:
        """输出小岛信息摘要

        Returns:
            str: 小岛信息摘要
        """
        return NameValueMappingToString({
            "小岛名": (self.name, False),
            "URL": (self.url, False),
            "分类": (self.category, False),
            "成员数": (self.members_count, False),
            "帖子数": (self.posts_count, False),
            "简介": (self.introduction, True)
        }, title="小岛信息摘要")
