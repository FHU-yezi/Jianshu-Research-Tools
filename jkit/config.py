from typing import Literal, Optional, TypeVar

from httpx import AsyncClient
from httpx._types import ProxiesTypes, TimeoutTypes
from msgspec import Struct, convert, field, to_builtins

from jkit.msgspec_constraints import NonEmptyStr

T = TypeVar("T", bound="ConfigObject")


class ConfigObject(Struct, eq=False, kw_only=True, gc=False):
    def _validate(self: T) -> T:
        return convert(to_builtins(self), type=self.__class__)


class _NetworkConfig(ConfigObject, eq=False, kw_only=True, gc=False):
    """网络配置"""

    # 使用的传输协议，HTTP/2 有助于提升性能
    protool: Literal["HTTP/1", "HTTP/2"] = "HTTP/2"

    # 代理配置，与 HTTPX proxies 选项支持类型相同
    proxies: Optional[ProxiesTypes] = None

    # 请求超时，与 HTTPX timeout 选项支持类型相同
    timeout: TimeoutTypes = 5

    def _get_http_client(self) -> AsyncClient:
        return AsyncClient(
            http2=self.protool == "HTTP/2",
            proxies=self.proxies,
            timeout=self.timeout,
        )

    def __setattr__(self, __name: str, __value: object) -> None:
        super().__setattr__(__name, __value)

        import jkit._network_request

        jkit._network_request.HTTP_CLIENT = self._get_http_client()


class _EndpointsConfig(ConfigObject, eq=False, kw_only=True, gc=False):
    """API 端点配置"""

    jianshu: NonEmptyStr = "https://www.jianshu.com"
    jpep: NonEmptyStr = "https://20221023.jianshubei.com/api"


class _ResourceCheckConfig(ConfigObject, eq=False, kw_only=True, gc=False):
    """资源检查配置"""

    # 从资源对象获取数据时自动进行资源检查
    # 检查结果将在同对象中缓存，以避免不必要的开销
    # 关闭后需要手动调用资源对象的 check 方法进行检查
    # 否则可能抛出 jkit.exceptions 范围以外的异常
    auto_check: bool = True

    # 强制对从安全数据来源构建的资源对象进行资源检查
    # 启用后可避免边界条件下的报错（如长时间保存资源对象）
    # 这将对性能造成影响
    force_check_safe_data: bool = False


class _DataValidationConfig(ConfigObject, eq=False, kw_only=True, gc=False):
    """数据校验配置"""

    # 是否启用数据校验
    # 遇特殊情况时可关闭以避免造成 ValidationError，此时不保证采集到的数据正确
    enabled: bool = True


class _Config(ConfigObject, eq=False, kw_only=True, gc=False):
    network: _NetworkConfig = field(default_factory=_NetworkConfig)
    endpoints: _EndpointsConfig = field(default_factory=_EndpointsConfig)
    resource_check: _ResourceCheckConfig = field(default_factory=_ResourceCheckConfig)
    data_validation: _DataValidationConfig = field(
        default_factory=_DataValidationConfig
    )


CONFIG = _Config()
