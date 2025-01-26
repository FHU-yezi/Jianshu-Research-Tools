from re import compile as regex_compile

ARTICLE_SLUG_REGEX = COLLECTION_SLUG_REGEX = USER_SLUG_REGEX = regex_compile(
    r"^[a-z0-9]{12}$|^[a-zA-z0-9]{6}$"
)
ISLAND_SLUG_REGEX = regex_compile(r"^[a-z0-9]{16}$")

ARTICLE_URL_REGEX = regex_compile(
    r"^https://www\.jianshu\.com/p/([a-z0-9]{12}|[a-zA-z0-9]{6})/?$"
)
COLLECTION_URL_REGEX = regex_compile(
    r"^https://www\.jianshu\.com/c/([a-z0-9]{12}|[a-zA-z0-9]{6})/?$"
)
ISLAND_URL_REGEX = regex_compile(r"^https://www\.jianshu\.com/g/[a-zA-Z0-9]{16}/?$")
NOTEBOOK_URL_REGEX = regex_compile(r"^https://www\.jianshu\.com/nb/\d{6,8}/?$")
USER_URL_REGEX = regex_compile(
    r"^https://www\.jianshu\.com/u/([a-z0-9]{12}|[a-zA-z0-9]{6})/?$"
)

USER_NAME_REGEX = regex_compile(r"^[\w]{,15}$")

JIANSHU_URL_REGEX = regex_compile(r"^https://www\.jianshu\.com/[a-zA-Z0-9/]*/?$")
USER_UPLOADED_URL_REGEX = regex_compile(r"^https?:\/\/.*/?$")

_HTML_TAG_REGEX = regex_compile("<.*?>")
_BLANK_LINES_REGEX = regex_compile("\n{2,}")

_NOTEBOOK_ID_MIN = 100000
_NOTEBOOK_ID_MAX = 99999999

_RATELIMIT_STATUS_CODE = 502
_RESOURCE_UNAVAILABLE_STATUS_CODE = 404
_ASSETS_ACTION_FAILED_STATUS_CODE = 422
