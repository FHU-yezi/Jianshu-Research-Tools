from __future__ import annotations

from typing import Literal, TypeVar

from httpx import AsyncClient
from httpx._types import HeaderTypes, ProxyTypes, TimeoutTypes
from msgspec import Struct, convert, field, to_builtins

from jkit import __version__
from jkit.constraints import NonEmptyStr

_DatasourceNameType = Literal["JIANSHU", "JPEP", "BEIJIAOYI"]

T = TypeVar("T", bound="_ConfigObject")


class _ConfigObject(Struct, eq=False, kw_only=True, gc=False):
    def _validate(self: T) -> T:
        return convert(to_builtins(self), type=self.__class__)


class _DatasourceConfig(_ConfigObject):
    # 数据源名称，不应被修改
    _name: _DatasourceNameType

    # 数据源 Endpoint（结尾不包含 / 字符）
    endpoint: NonEmptyStr

    # HTTP Headers
    headers: HeaderTypes

    # 使用的 HTTP 协议版本，HTTP/2 可提升性能
    http_version: Literal[1, 2]

    # 请求超时，具体配置方式详见 HTTPX 文档
    timeout: TimeoutTypes

    # 该数据源使用的代理，具体配置方式详见 HTTPX 文档
    proxy: ProxyTypes | None

    def _get_httpx_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self.endpoint,
            headers=self.headers,
            http2=self.http_version == 2,  # noqa: PLR2004
            timeout=self.timeout,
            proxy=self.proxy,
        )

    def __setattr__(self, __name: str, __value: object) -> None:
        super().__setattr__(__name, __value)

        from jkit._network import DATASOURCE_CLIENTS

        DATASOURCE_CLIENTS[self._name] = self._get_httpx_client()


class _DatasourcesList(_ConfigObject):
    # 简书
    jianshu: _DatasourceConfig

    # 简书积分兑换平台
    jpep: _DatasourceConfig

    # 贝交易平台
    beijiaoyi: _DatasourceConfig


class _ResourceCheckConfig(_ConfigObject):
    # 从资源对象获取数据时自动进行资源检查
    # 检查结果将在同对象中缓存，以避免不必要的开销
    # 关闭后需要手动调用资源对象的 check 方法进行检查
    # 否则可能抛出 jkit.exceptions 范围以外的异常
    auto_check: bool = True

    # 强制对从安全数据来源构建的资源对象进行资源检查
    # 启用后可避免边界条件下的报错（如长时间保存资源对象）
    # 这将对性能造成影响
    force_check_safe_data: bool = False


class _DataValidationConfig(_ConfigObject):
    # 是否启用数据校验
    # 遇特殊情况时可关闭以避免造成 ValidationError，此时不保证采集到的数据正确
    enabled: bool = True


class _Config(_ConfigObject):
    # 数据源配置
    datasources: _DatasourcesList = field(
        default_factory=lambda: _DatasourcesList(
            jianshu=_DatasourceConfig(
                _name="JIANSHU",
                endpoint="https://www.jianshu.com",
                headers={"User-Agent": f"JKit/{__version__}"},
                http_version=2,
                timeout=5,
                proxy=None,
            ),
            jpep=_DatasourceConfig(
                _name="JPEP",
                endpoint="https://20221023.jianshubei.com/api",
                headers={"User-Agent": f"JKit/{__version__}"},
                # 目前不支持 HTTP/2
                http_version=1,
                timeout=5,
                proxy=None,
            ),
            beijiaoyi=_DatasourceConfig(
                _name="BEIJIAOYI",
                endpoint="https://testapi.beijiaoyi.com/api",
                headers={"User-Agent": f"JKit/{__version__}"},
                # 目前不支持 HTTP/2
                http_version=1,
                timeout=5,
                proxy=None,
            ),
        )
    )
    # 资源检查配置
    resource_check: _ResourceCheckConfig = field(default_factory=_ResourceCheckConfig)
    # 数据校验配置
    data_validation: _DataValidationConfig = field(
        default_factory=_DataValidationConfig
    )


CONFIG = _Config()
