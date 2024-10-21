from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from httpx import HTTPStatusError
from msgspec import DecodeError

from jkit._base import DATA_OBJECT_CONFIG, DataObject, ResourceObject
from jkit._network_request import JSON_DECODER, get_json, send_post
from jkit._normalization import (
    normalize_assets_amount,
    normalize_assets_amount_precise,
    normalize_datetime,
    normalize_percentage,
)
from jkit.config import CONFIG
from jkit.credential import JianshuCredential
from jkit.exceptions import BalanceNotEnoughError, WeeklyConvertLimitExceededError
from jkit.msgspec_constraints import (
    NonEmptyStr,
    NonNegativeFloat,
    NormalizedDatetime,
    Percentage,
    PositiveInt,
)


class AssetsTransactionRecord(DataObject, **DATA_OBJECT_CONFIG):
    id: PositiveInt
    time: NormalizedDatetime
    type_id: PositiveInt
    type_text: NonEmptyStr
    amount: float
    amount_precise: Decimal


class FPRewardsRecord(DataObject, **DATA_OBJECT_CONFIG):
    time: NormalizedDatetime
    own_amount: Decimal
    level1_referral_amount: Decimal
    level2_referral_amount: Decimal
    total_amount: Decimal


class BenefitCardsInfo(DataObject, **DATA_OBJECT_CONFIG):
    total_amount: NonNegativeFloat
    estimated_benefits_percent: Percentage


class UnusedBenfitCardRecord(DataObject, **DATA_OBJECT_CONFIG):
    amount: NonNegativeFloat
    start_time: NormalizedDatetime
    end_time: NormalizedDatetime

    @property
    def is_valid(self) -> bool:
        return self.start_time <= datetime.now() <= self.end_time


class ActiveBenfitCardRecord(DataObject, **DATA_OBJECT_CONFIG):
    amount: NonNegativeFloat
    start_time: NormalizedDatetime
    end_time: NormalizedDatetime
    estimated_benefits_precent: NonNegativeFloat

    @property
    def is_valid(self) -> bool:
        return self.start_time <= datetime.now() <= self.end_time


class ExpiredBenfitCardRecord(DataObject, **DATA_OBJECT_CONFIG):
    amount: NonNegativeFloat
    start_time: NormalizedDatetime
    end_time: NormalizedDatetime
    benefits: float
    benfits_precise: Decimal

    @property
    def is_valid(self) -> bool:
        return self.start_time <= datetime.now() <= self.end_time


class Assets(ResourceObject):
    def __init__(self, *, credential: JianshuCredential) -> None:
        self._credential = credential

    async def iter_fp_records(
        self, *, max_id: Optional[int] = None
    ) -> AsyncGenerator[AssetsTransactionRecord, None]:
        now_max_id = max_id

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/transactions",
                params={"since_id": 0, "max_id": now_max_id}
                if now_max_id
                else {"since_id": 0},
                cookies=self._credential.cookies,
            )
            if not data["transactions"]:
                return

            now_max_id = data["transactions"][-1]["id"]

            for item in data["transactions"]:
                is_out = item["io_type"] == 2
                yield AssetsTransactionRecord(
                    id=item["id"],
                    time=normalize_datetime(item["time"]),
                    type_id=item["tn_type"],
                    type_text=item["display_name"],
                    amount=normalize_assets_amount(item["amount"])
                    * (-1 if is_out else 1),
                    amount_precise=normalize_assets_amount_precise(
                        item["amount_18"] * (-1 if is_out else 1)
                    ),
                )._validate()

    async def iter_ftn_records(
        self, *, max_id: Optional[int] = None
    ) -> AsyncGenerator[AssetsTransactionRecord, None]:
        now_max_id = max_id

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/jsb_transactions",
                params={"since_id": 0, "max_id": now_max_id}
                if now_max_id
                else {"since_id": 0},
                cookies=self._credential.cookies,
            )
            if not data["transactions"]:
                return

            now_max_id = data["transactions"][-1]["id"]

            for item in data["transactions"]:
                is_out = item["io_type"] == 2
                yield AssetsTransactionRecord(
                    id=item["id"],
                    time=normalize_datetime(item["time"]),
                    type_id=item["tn_type"],
                    type_text=item["display_name"],
                    amount=normalize_assets_amount(item["amount"])
                    * (-1 if is_out else 1),
                    amount_precise=normalize_assets_amount_precise(
                        item["amount_18"] * (-1 if is_out else 1)
                    ),
                )._validate()

    async def iter_fp_rewards_records(
        self, *, page_size: int = 10
    ) -> AsyncGenerator[FPRewardsRecord, None]:
        now_page = 1

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/jsd_rewards",
                params={"page": now_page, "count": page_size},
                cookies=self._credential.cookies,
            )
            if not data["transactions"]:
                return

            for item in data["transactions"]:
                yield FPRewardsRecord(
                    time=normalize_datetime(item["time"]),
                    own_amount=normalize_assets_amount_precise(item["own_reards18"]),
                    level1_referral_amount=normalize_assets_amount_precise(
                        item["referral_rewards18"]
                    ),
                    level2_referral_amount=normalize_assets_amount_precise(
                        item["grand_referral_rewards18"]
                    ),
                    total_amount=normalize_assets_amount_precise(
                        item["total_amount18"]
                    ),
                )._validate()

            now_page += 1

    @property
    async def benefit_cards_info(self) -> BenefitCardsInfo:
        data = await get_json(
            endpoint=CONFIG.endpoints.jianshu,
            path="/asimov/fp_wallets/benefit_cards/info",
            cookies=self._credential.cookies,
        )

        return BenefitCardsInfo(
            total_amount=float(normalize_assets_amount_precise(data["total_amount18"])),
            estimated_benefits_percent=normalize_percentage(
                data["total_estimated_benefits"]
            ),
        )._validate()

    async def iter_unused_benefit_cards(
        self, *, page_count: int = 10
    ) -> AsyncGenerator[UnusedBenfitCardRecord, None]:
        now_page = 1

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/benefit_cards/unsent",
                params={"page": now_page, "count": page_count},
                cookies=self._credential.cookies,
            )

            if not data["benefit_cards"]:
                return

            for item in data["benefit_cards"]:
                yield UnusedBenfitCardRecord(
                    amount=float(normalize_assets_amount_precise(item["amount18"])),
                    start_time=normalize_datetime(item["start_time"]),
                    end_time=normalize_datetime(item["end_time"]),
                )._validate()

            now_page += 1

    async def iter_active_benefit_cards(
        self, *, page_count: int = 10
    ) -> AsyncGenerator[ActiveBenfitCardRecord, None]:
        now_page = 1

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/benefit_cards/active",
                params={"page": now_page, "count": page_count},
                cookies=self._credential.cookies,
            )

            if not data["benefit_cards"]:
                return

            for item in data["benefit_cards"]:
                yield ActiveBenfitCardRecord(
                    amount=float(normalize_assets_amount_precise(item["amount18"])),
                    start_time=normalize_datetime(item["start_time"]),
                    end_time=normalize_datetime(item["end_time"]),
                    estimated_benefits_precent=item["estimated_benefits"] / 100,
                )._validate()

            now_page += 1

    async def iter_expired_benefit_cards(
        self, *, page_count: int = 10
    ) -> AsyncGenerator[ExpiredBenfitCardRecord, None]:
        now_page = 1

        while True:
            data = await get_json(
                endpoint=CONFIG.endpoints.jianshu,
                path="/asimov/fp_wallets/benefit_cards/expire",
                params={"page": now_page, "count": page_count},
                cookies=self._credential.cookies,
            )

            if not data["benefit_cards"]:
                return

            for item in data["benefit_cards"]:
                yield ExpiredBenfitCardRecord(
                    amount=float(normalize_assets_amount_precise(item["amount18"])),
                    start_time=normalize_datetime(item["start_time"]),
                    end_time=normalize_datetime(item["end_time"]),
                    benefits=round(
                        float(normalize_assets_amount_precise(item["benefits"])), 2
                    ),
                    benfits_precise=normalize_assets_amount_precise(item["benefits"]),
                )._validate()

            now_page += 1

    async def fp_to_ftn(self, /, amount: Union[int, float]) -> None:
        if amount <= 0:
            raise ValueError("转换的简书钻数量必须大于 0")

        try:
            with suppress(DecodeError):  # TODO
                await send_post(
                    endpoint=CONFIG.endpoints.jianshu,
                    path="/asimov/fp_wallets/exchange_jsb",
                    json={"count": str(amount)},
                    headers={"Accept": "application/json"},
                    cookies=self._credential.cookies,
                )
        except HTTPStatusError as e:
            if e.response.status_code == 422:
                data = JSON_DECODER.decode(e.response.content)
                if data["error"][0]["code"] == 18002:
                    raise BalanceNotEnoughError("简书钻余额不足") from None

                if data["error"][0]["code"] == 18005:
                    raise WeeklyConvertLimitExceededError(
                        "超出每周转换额度限制"
                    ) from None

            raise e from None

    async def ftn_to_fp(self, /, amount: Union[int, float]) -> None:
        if amount <= 0:
            raise ValueError("转换的简书贝数量必须大于 0")

        try:
            with suppress(DecodeError):  # TODO
                await send_post(
                    endpoint=CONFIG.endpoints.jianshu,
                    path="/asimov/fp_wallets/exchange_jsd",
                    json={"count": str(amount)},
                    headers={"Accept": "application/json"},
                    cookies=self._credential.cookies,
                )
        except HTTPStatusError as e:
            if e.response.status_code == 422:
                data = JSON_DECODER.decode(e.response.content)
                if data["error"][0]["code"] == 18002:
                    raise BalanceNotEnoughError("简书贝余额不足") from None

                if data["error"][0]["code"] == 18005:
                    raise WeeklyConvertLimitExceededError(
                        "超出每周转换额度限制"
                    ) from None

            raise e from None
