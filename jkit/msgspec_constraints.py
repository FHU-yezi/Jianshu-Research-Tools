from datetime import datetime
from typing import Annotated

from msgspec import Meta

from jkit.constants import (
    _NOTEBOOK_ID_MAX,
    _NOTEBOOK_ID_MIN,
    ARTICLE_SLUG_REGEX,
    ARTICLE_URL_REGEX,
    COLLECTION_SLUG_REGEX,
    COLLECTION_URL_REGEX,
    ISLAND_SLUG_REGEX,
    ISLAND_URL_REGEX,
    JIANSHU_URL_REGEX,
    NOTEBOOK_URL_REGEX,
    USER_NAME_REGEX,
    USER_SLUG_REGEX,
    USER_UPLOADED_URL_REGEX,
    USER_URL_REGEX,
)

PositiveInt = Annotated[int, Meta(gt=0)]
PositiveFloat = Annotated[float, Meta(gt=0)]
NonNegativeInt = Annotated[int, Meta(ge=0)]
NonNegativeFloat = Annotated[float, Meta(ge=0)]
NonEmptyStr = Annotated[str, Meta(min_length=1)]
Percentage = Annotated[float, Meta(ge=0, le=1)]
NormalizedDatetime = Annotated[datetime, Meta(tz=False)]

UserName = Annotated[str, Meta(pattern=USER_NAME_REGEX.pattern)]

JianshuUrl = Annotated[str, Meta(pattern=JIANSHU_URL_REGEX.pattern)]
UserUploadedUrl = Annotated[str, Meta(pattern=USER_UPLOADED_URL_REGEX.pattern)]
UserUrl = Annotated[str, Meta(pattern=USER_URL_REGEX.pattern)]
ArticleUrl = Annotated[str, Meta(pattern=ARTICLE_URL_REGEX.pattern)]
NotebookUrl = Annotated[str, Meta(pattern=NOTEBOOK_URL_REGEX.pattern)]
CollectionUrl = Annotated[str, Meta(pattern=COLLECTION_URL_REGEX.pattern)]
IslandUrl = Annotated[str, Meta(pattern=ISLAND_URL_REGEX.pattern)]

UserSlug = Annotated[str, Meta(pattern=USER_SLUG_REGEX.pattern)]
ArticleSlug = Annotated[str, Meta(pattern=ARTICLE_SLUG_REGEX.pattern)]
NotebookId = Annotated[int, Meta(ge=_NOTEBOOK_ID_MIN, le=_NOTEBOOK_ID_MAX)]
CollectionSlug = Annotated[str, Meta(pattern=COLLECTION_SLUG_REGEX.pattern)]
IslandSlug = Annotated[str, Meta(pattern=ISLAND_SLUG_REGEX.pattern)]
