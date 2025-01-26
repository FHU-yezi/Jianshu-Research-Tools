from __future__ import annotations

from collections.abc import AsyncGenerator
from enum import Enum
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


class PaymentChannels(Enum):
    WECHAT_PAY = "微信支付"
    ALIPAY = "支付宝"
    ANT_CREDIT_PAY = "蚂蚁花呗"


class PublisherInfoField(DataObject, frozen=True):
    id: PositiveInt
    name: NonEmptyStr
    hashed_name: NonEmptyStr
    avatar_url: NonEmptyStr | None
    credit: NonNegativeInt


class FTNMacketOrderRecord(DataObject, frozen=True):
    id: PositiveInt
    price: PositiveFloat

    total_amount: PositiveInt
    traded_amount: NonNegativeInt
    tradable_amount: NonNegativeInt
    minimum_trade_amount: PositiveInt

    traded_count: NonNegativeInt
    publish_time: NormalizedDatetime
    supported_payment_channels: tuple[PaymentChannels, ...]

    publisher_info: PublisherInfoField


class FTNMacket(ResourceObject):
    async def iter_orders(
        self,
        *,
        type: Literal["BUY", "SELL"],
        start_page: int = 1,
    ) -> AsyncGenerator[FTNMacketOrderRecord, None]:
        now_page = start_page
        while True:
            data = await send_request(
                datasource="JPEP",
                method="POST",
                # TODO
                path=f"/getList/furnish.bei/?page={now_page}",
                body={
                    "filter": [
                        {"trade": 1 if type == "BUY" else 0},
                        {"status": 1},
                        {"finish": 0},
                        {"tradable": {">": "0"}},
                    ],
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
                yield FTNMacketOrderRecord(
                    id=item["id"],
                    price=item["price"],
                    total_amount=item["totalNum"],
                    traded_amount=item["tradeNum"],
                    tradable_amount=item["tradable"],
                    minimum_trade_amount=item["minNum"],
                    traded_count=item["tradeCount"],
                    publish_time=normalize_datetime(item["pub_date"]),
                    supported_payment_channels=tuple(
                        {
                            1: PaymentChannels.WECHAT_PAY,
                            2: PaymentChannels.ALIPAY,
                            3: PaymentChannels.ANT_CREDIT_PAY,
                        }[int(x)]
                        for x in item["member.user"][0]["pay_types"].split("|")
                    )
                    if item["member.user"][0]["pay_types"]
                    else (),
                    publisher_info=PublisherInfoField(
                        id=item["member.user"][0]["id"],
                        name=item["member.user"][0]["username"],
                        hashed_name=item["member.user"][0]["username_md5"],
                        avatar_url=item["member.user"][0]["avatarUrl"]
                        if item["member.user"][0]["avatarUrl"]
                        else None,
                        credit=item["member.user"][0]["credit"],
                    ),
                )._validate()

            now_page += 1
