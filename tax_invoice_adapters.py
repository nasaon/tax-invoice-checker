from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import pandas as pd
import requests

BUSINESS_NUMBER_RE = re.compile(r"^\d{3}-\d{2}-\d{5}$")


@dataclass(frozen=True)
class VerificationResult:
    is_registered: bool
    reason: str | None = None


class BusinessNumberVerifier(Protocol):
    def verify(self, business_number: str) -> VerificationResult:
        ...


class LocalFormatVerifier:
    """Format-only local verification — no external API call."""

    def verify(self, business_number: str) -> VerificationResult:
        if not BUSINESS_NUMBER_RE.match(business_number):
            return VerificationResult(is_registered=False, reason="사업자번호 형식이 올바르지 않습니다 (XXX-XX-XXXXX).")
        return VerificationResult(is_registered=True)


class NtsPublicApiVerifier:
    """Verifies business number registration via NTS API (공공데이터포털).

    API: https://api.odcloud.kr/api/nts-businessman/v1/status
    Requires a service key from https://www.data.go.kr
    """

    _ENDPOINT = "https://api.odcloud.kr/api/nts-businessman/v1/status"

    def __init__(self, service_key: str | object) -> None:
        if hasattr(service_key, "get_secret_value"):
            self._service_key: str = service_key.get_secret_value()  # type: ignore[union-attr]
        else:
            self._service_key = str(service_key)

    def __repr__(self) -> str:
        return "NtsPublicApiVerifier(service_key=***)"

    def verify(self, business_number: str) -> VerificationResult:
        raw_number = business_number.replace("-", "")
        # data.go.kr API는 serviceKey 쿼리 파라미터를 사용합니다 (API 제약사항)
        response = requests.post(
            self._ENDPOINT,
            params={"serviceKey": self._service_key, "returnType": "JSON"},
            json={"b_no": [raw_number]},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [{}])[0]
        tax_type = data.get("tax_type", "")
        if "등록되지 않은" in tax_type or not data.get("b_stt_cd"):
            return VerificationResult(
                is_registered=False,
                reason=tax_type or "등록되지 않은 사업자번호입니다.",
            )
        return VerificationResult(is_registered=True)


@dataclass(frozen=True)
class IssuanceResult:
    queue_state: str
    message: str
    external_id: str | None = None


class IssuanceAdapter(Protocol):
    name: str

    def preview_issue(self, row: pd.Series) -> IssuanceResult:
        ...


class QueuePreviewAdapter:
    name = "queue-preview"

    def preview_issue(self, row: pd.Series) -> IssuanceResult:
        if row.get("상태코드") != "ready-to-send":
            return IssuanceResult(
                queue_state="rejected",
                message="발행 대기 상태의 행만 큐 미리보기를 생성할 수 있습니다.",
                external_id=None,
            )

        return IssuanceResult(
            queue_state="queued",
            message="실제 발행 대신 발행 큐 생성만 수행합니다.",
            external_id=None,
        )
