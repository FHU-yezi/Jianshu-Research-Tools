from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Callable, ClassVar, TypeVar

from msgspec import Struct, convert, to_builtins
from msgspec import ValidationError as MsgspecValidationError

from jkit.config import CONFIG
from jkit.exceptions import ValidationError

T = TypeVar("T", bound="DataObject")
P1 = TypeVar("P1", bound="CheckableMixin")
P2 = TypeVar("P2", bound="SlugAndUrlMixin")
P3 = TypeVar("P3", bound="IdAndUrlMixin")


class DataObject(Struct, frozen=True, eq=True, kw_only=True):
    def _validate(self: T) -> T:
        if not CONFIG.data_validation.enabled:
            return self

        try:
            return convert(to_builtins(self), type=self.__class__)
        except MsgspecValidationError as e:
            raise ValidationError(e.args[0]) from None

    def __repr__(self) -> str:
        field_strings: list[str] = []
        for field in self.__struct_fields__:
            value = self.__getattribute__(field)

            if isinstance(value, str) and len(value) >= 100:  # noqa: PLR2004
                formatted_value = value[:100] + "[truncated...]"
            else:
                formatted_value = value.__repr__()

            field_strings.append(f"{field}={formatted_value}")

        return (
            self.__class__.__name__ + "(\n    " + ",\n    ".join(field_strings) + "\n)"
        )


class ResourceObject:
    pass


class CheckableMixin(metaclass=ABCMeta):
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


class SlugAndUrlMixin:
    _slug_check_func: ClassVar[Callable[[str], bool] | None] = None
    _slug_to_url_func: ClassVar[Callable[[str], str] | None] = None
    _url_to_slug_func: ClassVar[Callable[[str], str] | None] = None

    def __init__(self, *, slug: str | None = None, url: str | None = None) -> None:
        del slug, url

        self._slug = ""

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
        if not self.__class__._slug_to_url_func:
            raise AssertionError

        return self.__class__._slug_to_url_func(self._slug)

    @classmethod
    def _check_params(
        cls,
        *,
        object_readable_name: str,
        slug: str | None,
        url: str | None,
    ) -> str:
        # 如果同时提供了 Slug 和 Url
        if slug is not None and url is not None:
            raise ValueError(
                f"{object_readable_name} Slug 与{object_readable_name}链接不可同时提供"
            )

        # 如果提供了 Slug
        if slug is not None:
            if not cls._slug_check_func:
                raise AssertionError

            if not cls._slug_check_func(slug):
                raise ValueError(f"{slug} 不是有效的{object_readable_name} Slug")

            return slug
        # 如果提供了 Url
        elif url is not None:  # noqa: RET505
            if not cls._url_to_slug_func:
                raise AssertionError

            # 转换函数中会对 Url 进行检查，并在 Url 无效时抛出异常
            return cls._url_to_slug_func(url)

        # 如果 Slug 与 Url 均未提供
        raise ValueError(
            f"必须提供{object_readable_name} Slug 或{object_readable_name}链接"
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.slug == other.slug

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(slug="{self.slug}")'


class IdAndUrlMixin(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def from_id(cls: type[P3], id: int, /) -> P3:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_url(cls: type[P3], url: str, /) -> P3:
        raise NotImplementedError

    @property
    @abstractmethod
    def id(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id="{self.id}")'
