from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Callable, ClassVar, TypeVar

from msgspec import Struct, convert, to_builtins
from msgspec import ValidationError as MsgspecValidationError

from jkit.config import CONFIG
from jkit.exceptions import InvalidIdentifierError, ValidationError

T = TypeVar("T", bound="DataObject")
P1 = TypeVar("P1", bound="CheckableResourceMixin")
P2 = TypeVar("P2", bound="SlugAndUrlResourceMixin")
P3 = TypeVar("P3", bound="IdAndUrlResourceMixin")


def _check_func_placeholder(x: Any) -> bool:  # noqa: ANN401
    raise NotImplementedError


def _convert_func_placeholder(x: Any) -> Any:  # noqa: ANN401
    raise NotImplementedError


class ResourceObject:
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class SlugAndUrlResourceMixin:
    _resource_readable_name: ClassVar[str] = ""

    _slug_check_func: Callable[[str], bool] = _check_func_placeholder
    _url_check_func: Callable[[str], bool] = _check_func_placeholder

    _url_to_slug_func: Callable[[str], str] = _convert_func_placeholder
    _slug_to_url_func: Callable[[str], str] = _convert_func_placeholder

    def __init__(self, *, slug: str | None = None, url: str | None = None) -> None:
        class_ = self.__class__
        name = class_._resource_readable_name

        if slug is None and url is None:
            raise ValueError(f"必须提供 {name} Slug 或 {name} Url")

        if slug is not None and url is not None:
            raise ValueError(f"{name} Slug 与 {name} Url 不可同时提供")

        if slug is not None:
            if not class_._slug_check_func(slug):
                raise InvalidIdentifierError(f"{slug} 不是有效的 {name} Slug")

            self._slug = slug

        if url is not None:
            if not class_._url_check_func(url):
                raise InvalidIdentifierError(f"{url} 不是有效的 {name} Url")

            self._slug = class_._url_to_slug_func(url)

    @classmethod
    def from_slug(cls: type[P2], slug: str, /) -> P2:
        return cls(slug=slug)

    @classmethod
    def from_url(cls: type[P2], url: str, /) -> P2:
        return cls(url=url)

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def url(self) -> str:
        return self.__class__._slug_to_url_func(self._slug)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.slug == other.slug

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(slug="{self.slug}")'


class IdAndUrlResourceMixin:
    _resource_readable_name: ClassVar[str] = ""

    _id_check_func: Callable[[int], bool] = _check_func_placeholder
    _url_check_func: Callable[[str], bool] = _check_func_placeholder

    _url_to_id_func: Callable[[str], int] = _convert_func_placeholder
    _id_to_url_func: Callable[[int], str] = _convert_func_placeholder

    def __init__(self, *, id: int | None = None, url: str | None = None) -> None:
        class_ = self.__class__
        name = class_._resource_readable_name

        if id is None and url is None:
            raise ValueError(f"必须提供 {name} Id 或 {name} Url")

        if id is not None and url is not None:
            raise ValueError(f"{name} Id 与 {name} Url 不可同时提供")

        if id is not None:
            if not class_._id_check_func(id):
                raise InvalidIdentifierError(f"{id} 不是有效的 {name} Id")

            self._id = id

        if url is not None:
            if not class_._url_check_func(url):
                raise InvalidIdentifierError(f"{url} 不是有效的 {name} Url")

            self._id = class_._url_to_id_func(url)

    @classmethod
    def from_id(cls: type[P3], id: int, /) -> P3:
        return cls(id=id)

    @classmethod
    def from_url(cls: type[P3], url: str, /) -> P3:
        return cls(url=url)

    @property
    def id(self) -> int:
        return self._id

    @property
    def url(self) -> str:
        return self.__class__._id_to_url_func(self._id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self._id == other._id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id})"


class CheckableResourceMixin(metaclass=ABCMeta):
    def __init__(self) -> None:
        self._checked = False

    @abstractmethod
    async def check(self) -> None:
        raise NotImplementedError

    async def _require_check(self) -> None:
        if self._checked or not CONFIG.resource_check.auto_check:
            return

        await self.check()
        self._checked = True

    def _as_checked(self: P1) -> P1:
        if not CONFIG.resource_check.force_check_safe_data:
            self._checked = True

        return self


class DataObject(Struct, frozen=True, eq=True, kw_only=True):
    def _validate(self: T) -> T:
        if not CONFIG.data_validation.enabled:
            return self

        try:
            return convert(to_builtins(self), type=self.__class__)
        except MsgspecValidationError as e:
            raise ValidationError(e.args[0]) from None

    def __repr__(self) -> str:
        result: list[str] = []

        for key in self.__struct_fields__:
            value = getattr(self, key)

            # 对于嵌套 DataObject，单独进行处理
            if isinstance(value, DataObject):
                formatted_value = value.__repr__()

                # 处理首字段缩进
                formatted_value = formatted_value.replace(
                    f"{value.__class__.__name__}(\n    ",
                    f"{value.__class__.__name__}(\n        ",
                )

                # 处理字段嵌套缩进
                formatted_value = formatted_value.replace(",\n    ", ",\n        ")

                # 处理末尾括号缩进
                formatted_value = formatted_value[:-1] + "    )"

                result.append(f"{key}={formatted_value}")
                continue

            # 截断长度大于 100 的字符串
            if isinstance(value, str) and len(value) > 100:  # noqa: PLR2004
                value = value[:100] + "..."

            result.append(f"{key}={value!r}")

        return "\n".join(
            (
                f"{self.__class__.__name__}(",
                "    " + ",\n    ".join(result),
                ")",
            )
        )


class CredentialObject:
    @property
    def headers(self) -> dict[str, str]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
