from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import suppress
from decimal import Decimal
from re import compile as re_compile
from typing import Literal

from httpx import HTTPStatusError
from msgspec import DecodeError

from jkit._base import DataObject, ResourceObject
from jkit._network import JSON_DECODER, send_request
from jkit._normalization import (
    normalize_assets_amount_precise,
    normalize_datetime,
    normalize_percentage,
)
from jkit.constants import _ASSETS_ACTION_FAILED_STATUS_CODE
from jkit.constraints import (
    NonEmptyStr,
    NonNegativeFloat,
    NonNegativeInt,
    NormalizedDatetime,
    Percentage,
    PositiveInt,
)
from jkit.credentials import JianshuCredential
from jkit.exceptions import BalanceNotEnoughError, WeeklyConvertLimitExceededError

_HTML_INNER_JSON_REGEX = re_compile(r"__INITIAL_STATE__=(.*);\(function")

AssetsTransactionType = Literal["INCOME", "EXPENSE"]
BenefitCardType = Literal["PENDING", "ACTIVE", "EXPIRED"]


class AssetsInfoData(DataObject, frozen=True):
    fp_amount: Decimal
    ftn_amount: Decimal
    assets_amount: Decimal
    converting_fp_amount: Decimal


class TransactionData(DataObject, frozen=True):
    id: PositiveInt
    time: NormalizedDatetime
    type: AssetsTransactionType
    category: NonEmptyStr
    amount: Decimal


class FpHoldingRewardData(DataObject, frozen=True):
    time: NormalizedDatetime
    own_amount: Decimal
    level1_referral_amount: Decimal
    level2_referral_amount: Decimal
    total_amount: Decimal


class BenefitCardsInfoData(DataObject, frozen=True):
    total_amount: NonNegativeInt
    estimated_benefits_percent: Percentage


class BenefitCardData(DataObject, frozen=True):
    type: BenefitCardType
    amount: NonNegativeInt
    start_time: NormalizedDatetime
    end_time: NormalizedDatetime
    estimated_benefits_precent: NonNegativeFloat | None


class AssetsWallet(ResourceObject):
    def __init__(self, *, credential: JianshuCredential) -> None:
        self._credential = credential

    @property
    async def assets_info(self) -> AssetsInfoData:
        html = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/mobile/fp/",
            credential=self._credential,
            response_type="HTML",
        )
        data = JSON_DECODER.decode(_HTML_INNER_JSON_REGEX.findall(html)[0])

        return AssetsInfoData(
            fp_amount=normalize_assets_amount_precise(
                data["ruby"]["wallet"]["assets"]["jsd_amount18"]
            ),
            ftn_amount=normalize_assets_amount_precise(
                data["ruby"]["wallet"]["assets"]["jsb_amount18"]
            ),
            assets_amount=normalize_assets_amount_precise(
                data["ruby"]["wallet"]["assets"]["total_assets18"]
            ),
            converting_fp_amount=normalize_assets_amount_precise(
                data["ruby"]["wallet"]["assets"]["exchanging_jsb18"]
            ),
        )._validate()

    async def iter_transactions(
        self,
        *,
        type: Literal["FP", "FTN"],
        min_id: int = 0,
        max_id: int | None = None,
    ) -> AsyncGenerator[TransactionData, None]:
        current_max_id = max_id

        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path="/asimov/fp_wallets/transactions"
                if type == "FP"
                else "/asimov/fp_wallets/jsb_transactions",
                params={
                    "since_id": min_id,
                    "max_id": current_max_id,
                }
                if current_max_id
                else {"since_id": min_id},
                credential=self._credential,
                response_type="JSON",
            )
            if not data["transactions"]:
                return

            current_max_id = data["transactions"][-1]["id"]

            for item in data["transactions"]:
                # 1：收入 2：支出
                transaction_type: AssetsTransactionType = (
                    "INCOME" if item["io_type"] == 1 else "EXPENSE"
                )
                yield TransactionData(
                    id=item["id"],
                    time=normalize_datetime(item["time"]),
                    type=transaction_type,
                    category=item["display_name"],
                    amount=normalize_assets_amount_precise(
                        # 将获得与消耗数值统一为正
                        abs(item["amount_18"])
                    ),
                )._validate()

    async def iter_fp_holding_rewards(
        self,
    ) -> AsyncGenerator[FpHoldingRewardData, None]:
        current_page = 1

        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path="/asimov/fp_wallets/jsd_rewards",
                params={"page": current_page, "count": 20},
                credential=self._credential,
                response_type="JSON",
            )
            if not data["transactions"]:
                return

            for item in data["transactions"]:
                yield FpHoldingRewardData(
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

            current_page += 1

    @property
    async def benefit_cards_info(self) -> BenefitCardsInfoData:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/fp_wallets/benefit_cards/info",
            credential=self._credential,
            response_type="JSON",
        )

        return BenefitCardsInfoData(
            total_amount=int(normalize_assets_amount_precise(data["total_amount18"])),
            estimated_benefits_percent=normalize_percentage(
                data["total_estimated_benefits"]
            ),
        )._validate()

    async def iter_benefit_cards(
        self, *, type: BenefitCardType
    ) -> AsyncGenerator[BenefitCardData, None]:
        current_page = 1

        while True:
            data = await send_request(
                datasource="JIANSHU",
                method="GET",
                path={
                    "PENDING": "/asimov/fp_wallets/benefit_cards/unsent",
                    "ACTIVE": "/asimov/fp_wallets/benefit_cards/active",
                    "EXPIRED": "/asimov/fp_wallets/benefit_cards/expire",
                }[type],
                params={"page": current_page, "count": 20},
                credential=self._credential,
                response_type="JSON",
            )

            if not data["benefit_cards"]:
                return

            for item in data["benefit_cards"]:
                yield BenefitCardData(
                    type=type,
                    amount=int(normalize_assets_amount_precise(item["amount18"])),
                    start_time=normalize_datetime(item["start_time"]),
                    end_time=normalize_datetime(item["end_time"]),
                    estimated_benefits_precent=item["estimated_benefits"] / 100
                    if "estimated_benefits" in item
                    else None,
                )._validate()

            current_page += 1

    # FIXME: 转换数量为 0
    async def fp_to_ftn(self, amount: int | float, /) -> None:
        if amount <= 0:
            raise ValueError("转换的简书钻数量必须大于 0")

        try:
            # TODO: send_request 函数支持 response_type=None
            with suppress(DecodeError):
                await send_request(
                    datasource="JIANSHU",
                    method="POST",
                    path="/asimov/fp_wallets/exchange_jsb",
                    body={"count": amount},
                    credential=self._credential,
                    response_type="JSON",
                )
        except HTTPStatusError as e:
            if e.response.status_code == _ASSETS_ACTION_FAILED_STATUS_CODE:
                data = JSON_DECODER.decode(e.response.content)
                if data["error"][0]["code"] == 18002:  # noqa: PLR2004
                    raise BalanceNotEnoughError("简书钻余额不足") from None

                if data["error"][0]["code"] == 18005:  # noqa: PLR2004
                    raise WeeklyConvertLimitExceededError(
                        "超出每周转换额度限制"
                    ) from None

            raise e from None

    # FIXME: 转换数量为 0
    async def ftn_to_fp(self, amount: int | float, /) -> None:
        if amount <= 0:
            raise ValueError("转换的简书贝数量必须大于 0")

        try:
            # TODO: send_request 函数支持 response_type=None
            with suppress(DecodeError):
                await send_request(
                    datasource="JIANSHU",
                    method="POST",
                    path="/asimov/fp_wallets/exchange_jsd",
                    body={"count": amount},
                    credential=self._credential,
                    response_type="JSON",
                )
        except HTTPStatusError as e:
            if e.response.status_code == _ASSETS_ACTION_FAILED_STATUS_CODE:
                data = JSON_DECODER.decode(e.response.content)
                if data["error"][0]["code"] == 18002:  # noqa: PLR2004
                    raise BalanceNotEnoughError("简书贝余额不足") from None

                if data["error"][0]["code"] == 18005:  # noqa: PLR2004
                    raise WeeklyConvertLimitExceededError(
                        "超出每周转换额度限制"
                    ) from None
            raise e from None
