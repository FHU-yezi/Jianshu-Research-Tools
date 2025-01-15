from jkit.constants import (
    _NOTEBOOK_ID_MAX,
    _NOTEBOOK_ID_MIN,
    ARTICLE_SLUG_REGEX,
    ARTICLE_URL_REGEX,
    COLLECTION_SLUG_REGEX,
    COLLECTION_URL_REGEX,
    ISLAND_SLUG_REGEX,
    ISLAND_URL_REGEX,
    NOTEBOOK_URL_REGEX,
    USER_SLUG_REGEX,
    USER_URL_REGEX,
)


def is_user_url(x: str, /) -> bool:
    return bool(USER_URL_REGEX.fullmatch(x))


def is_article_url(x: str, /) -> bool:
    return bool(ARTICLE_URL_REGEX.fullmatch(x))


def is_notebook_url(x: str, /) -> bool:
    return bool(NOTEBOOK_URL_REGEX.fullmatch(x))


def is_collection_url(x: str, /) -> bool:
    return bool(COLLECTION_URL_REGEX.fullmatch(x))


def is_island_url(x: str, /) -> bool:
    return bool(ISLAND_URL_REGEX.fullmatch(x))


def is_user_slug(x: str, /) -> bool:
    return bool(USER_SLUG_REGEX.fullmatch(x))


def is_article_slug(x: str, /) -> bool:
    return bool(ARTICLE_SLUG_REGEX.fullmatch(x))


def is_notebook_id(x: int, /) -> bool:
    return _NOTEBOOK_ID_MIN <= x <= _NOTEBOOK_ID_MAX


def is_collection_slug(x: str, /) -> bool:
    return bool(COLLECTION_SLUG_REGEX.fullmatch(x))


def is_island_slug(x: str, /) -> bool:
    return bool(ISLAND_SLUG_REGEX.fullmatch(x))
