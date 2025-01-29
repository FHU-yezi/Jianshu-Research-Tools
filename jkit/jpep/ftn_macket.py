from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Literal

from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit._normalization import normalize_datetime
from jkit.constraints import (
    NonEmptyStr,
    NonNegativeInt,
    NormalizedDatetime,
    PositiveFloat,
    PositiveInt,
)

FtnMarketOrderSupportedPaymentChannelsType = Literal[
    "WECHAT_PAY", "ALIPAY", "ANT_CREDIT_PAY"
]


class _PublisherInfoField(DataObject, frozen=True):
    id: PositiveInt
    name: NonEmptyStr

    hashed_name: NonEmptyStr
    avatar_url: NonEmptyStr | None
    credit: NonNegativeInt


class FtnMacketOrderData(DataObject, frozen=True):
    id: PositiveInt

    price: PositiveFloat
    total_amount: PositiveInt
    traded_amount: NonNegativeInt
    tradable_amount: NonNegativeInt
    minimum_trade_amount: PositiveInt

    completed_trades_count: NonNegativeInt
    publish_time: NormalizedDatetime
    supported_payment_channels: tuple[FtnMarketOrderSupportedPaymentChannelsType, ...]

    publisher_info: _PublisherInfoField


class FtnMacket(ResourceObject):
    async def iter_orders(
        self,
        *,
        type: Literal["BUY", "SELL"],
        start_page: int = 1,
    ) -> AsyncGenerator[FtnMacketOrderData, None]:
        current_page = start_page

        while True:
            data = await send_request(
                datasource="JPEP",
                method="POST",
                path=f"/getList/furnish.bei/?page={current_page}",
                params={"page": current_page},
                body={
                    "filter": [
                        # 0：卖单 1：买单
                        {"trade": 1 if type == "BUY" else 0},
                        {"status": 1},
                        {"finish": 0},
                        {"tradable": {">": "0"}},
                    ],
                    # 买单价格正序，卖单价格倒序
                    "sort": "price,pub_date" if type == "BUY" else "-price,pub_date",
                    "bind": [
                        {
                            "member.user": {
                                "filter": [{"id": "{{uid}}"}],
                                "addField": [{"username_md5": "username_md5"}],
                                "fields": "id,username,avatarUrl,credit,pay_types",
                            }
                        }
                    ],
                    "addField": [
                        {"tradeCount": "tradeCount"},
                        {"tradeNum": "tradeNum"},
                    ],
                },
                response_type="JSON",
            )

            if not data["data"]:
                break

            for item in data["data"]:
                item_user = item["member.user"][0]

                yield FtnMacketOrderData(
                    id=item["id"],
                    price=item["price"],
                    total_amount=item["totalNum"],
                    traded_amount=item["tradeNum"],
                    tradable_amount=item["tradable"],
                    minimum_trade_amount=item["minNum"],
                    completed_trades_count=item["tradeCount"],
                    publish_time=normalize_datetime(item["pub_date"]),
                    # TODO: 优化类型检查
                    supported_payment_channels=tuple(
                        {
                            1: "WECHAT_PAY",
                            2: "ALIPAY",
                            3: "ANT_CREDIT_PAY",
                        }[int(x)]
                        for x in item_user["pay_types"].split("|")
                    )
                    if item_user["pay_types"]
                    else (),  # type: ignore
                    publisher_info=_PublisherInfoField(
                        id=item_user["id"],
                        name=item_user["username"],
                        hashed_name=item_user["username_md5"],
                        avatar_url=item_user["avatarUrl"]
                        if item_user["avatarUrl"]
                        else None,
                        credit=item_user["credit"],
                    ),
                )._validate()

            current_page += 1
