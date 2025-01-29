from jkit._base import DataObject, ResourceObject
from jkit._network import send_request
from jkit.constraints import NonNegativeFloat


class RulesData(DataObject, frozen=True):
    opening: bool

    ftn_trade_fee: NonNegativeFloat
    goods_trade_fee: NonNegativeFloat

    ftn_buy_trade_minimum_price: NonNegativeFloat
    ftn_sell_trade_minimum_price: NonNegativeFloat


class Rules(ResourceObject):
    async def get_rules(self) -> RulesData:
        data = await send_request(
            datasource="JPEP",
            method="POST",
            path="/getList/furnish.setting/1/",
            body={"fields": "isClose,fee,shop_fee,minimum_price,buy_minimum_price"},
            response_type="JSON",
        )

        return RulesData(
            opening=not bool(data["data"]["isClose"]),
            ftn_trade_fee=data["data"]["fee"],
            goods_trade_fee=data["data"]["shop_fee"],
            ftn_buy_trade_minimum_price=data["data"]["buy_minimum_price"],
            ftn_sell_trade_minimum_price=data["data"]["minimum_price"],
        )._validate()
