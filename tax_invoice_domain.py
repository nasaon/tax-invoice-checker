from __future__ import annotations

from hashlib import sha1
import re

import pandas as pd

TEMPLATE_VERSION = "2026-05-v1"

REQUIRED_COLUMNS = [
    "템플릿버전",
    "거래구분",
    "작성일",
    "거래처명",
    "거래처사업자번호",
    "품목",
    "공급가액",
    "세액",
]

OPTIONAL_COLUMNS = [
    "과세유형",
    "발행상태",
]

STATUS_LABELS = {
    "draft": "초안",
    "validated": "검증 완료",
    "needs-party": "거래처 보완",
    "ready-to-send": "발행 대기",
    "failed": "검증 실패",
    "sent": "발행 완료",
}

PARTNER_NAMES = [
    "스튜디오 모루",
    "퍼플 미디어",
    "플로우 커머스",
    "오후 다섯시",
    "청명 디자인",
    "한결 물산",
    "브라이트 랩",
    "모노 플랫폼",
]

ITEM_NAMES = [
    "디자인 용역",
    "광고 집행비",
    "정산 수수료",
    "행사 운영비",
    "콘텐츠 제작비",
    "호스팅 이용료",
    "플랫폼 사용료",
    "브랜딩 컨설팅",
]

BUSINESS_NUMBER_RE = re.compile(r"^\d{3}-\d{2}-\d{5}$")


def _format_business_number(seed: int) -> str:
    front = 100 + (seed * 7) % 900
    middle = 10 + (seed * 3) % 90
    back = 10000 + (seed * 137) % 90000
    return f"{front:03d}-{middle:02d}-{back:05d}"


def make_sample_template(count: int = 50, include_issue_rows: bool = True) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(count):
        supply_amount = 100000 + (index % 9) * 50000 + (index // 9) * 15000
        tax_amount = round(supply_amount * 0.1)
        row = {
            "템플릿버전": TEMPLATE_VERSION,
            "거래구분": "매출" if index % 2 == 0 else "매입",
            "작성일": f"2026-05-{(index % 28) + 1:02d}",
            "거래처명": PARTNER_NAMES[index % len(PARTNER_NAMES)],
            "거래처사업자번호": _format_business_number(index + 1),
            "품목": ITEM_NAMES[index % len(ITEM_NAMES)],
            "공급가액": supply_amount,
            "세액": tax_amount,
            "과세유형": "과세",
            "발행상태": "",
        }

        if include_issue_rows:
            issue_pattern = index % 10
            if issue_pattern == 1:
                row["거래처사업자번호"] = ""
            elif issue_pattern == 2:
                row["거래처사업자번호"] = "1234567890"
            elif issue_pattern == 3:
                row["세액"] = tax_amount + 1000
            elif issue_pattern == 4:
                row["발행상태"] = "발행완료"

        rows.append(row)

    return pd.DataFrame(rows)


def make_self_test_template(count: int = 100) -> pd.DataFrame:
    return make_sample_template(count=count, include_issue_rows=False)


def export_sample_excel(path: str, count: int = 50, include_issue_rows: bool = True) -> None:
    make_sample_template(count=count, include_issue_rows=include_issue_rows).to_excel(path, index=False)


def export_self_test_excel(path: str, count: int = 100) -> None:
    make_self_test_template(count=count).to_excel(path, index=False)


def normalize_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = dataframe.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]

    for column in REQUIRED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""

    for column in OPTIONAL_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""

    if "과세유형" in normalized.columns:
        normalized["과세유형"] = normalized["과세유형"].replace("", "과세")

    return normalized


def build_idempotency_key(
    issue_date: str,
    business_number: str,
    item_name: str,
    supply_amount: int,
) -> str:
    base = "|".join(
        [
            issue_date.strip(),
            business_number.strip(),
            item_name.strip(),
            str(supply_amount),
        ]
    )
    return sha1(base.encode("utf-8")).hexdigest()[:16]


def validate_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_dataframe(dataframe)
    records: list[dict[str, object]] = []

    for row_number, row in normalized.iterrows():
        issues: list[str] = []
        lifecycle_state = "draft"

        template_version = str(row.get("템플릿버전", "")).strip()
        direction = str(row.get("거래구분", "")).strip()
        issue_date = str(row.get("작성일", "")).strip()
        partner_name = str(row.get("거래처명", "")).strip()
        business_number = str(row.get("거래처사업자번호", "")).strip()
        item_name = str(row.get("품목", "")).strip()
        tax_type = str(row.get("과세유형", "과세")).strip() or "과세"
        raw_issue_status = str(row.get("발행상태", "")).strip()
        supply_amount = pd.to_numeric(row.get("공급가액", 0), errors="coerce")
        tax_amount = pd.to_numeric(row.get("세액", 0), errors="coerce")

        if template_version != TEMPLATE_VERSION:
            issues.append(f"템플릿버전이 {TEMPLATE_VERSION}와 일치하지 않습니다.")
        if not direction:
            issues.append("거래구분이 비어 있습니다.")
        if not issue_date:
            issues.append("작성일이 비어 있습니다.")
        if not partner_name:
            issues.append("거래처명이 비어 있습니다.")
        if not item_name:
            issues.append("품목이 비어 있습니다.")
        if tax_type != "과세":
            issues.append("현재 버전은 과세 거래만 지원합니다.")
        if pd.isna(supply_amount):
            issues.append("공급가액이 숫자가 아닙니다.")
            supply_amount = 0
        if pd.isna(tax_amount):
            issues.append("세액이 숫자가 아닙니다.")
            tax_amount = 0

        supply_amount = int(supply_amount)
        tax_amount = int(tax_amount)
        total_amount = supply_amount + tax_amount
        idempotency_key = build_idempotency_key(
            issue_date=issue_date,
            business_number=business_number,
            item_name=item_name,
            supply_amount=supply_amount,
        )

        if business_number:
            if not BUSINESS_NUMBER_RE.match(business_number):
                issues.append("거래처 사업자번호 형식이 올바르지 않습니다.")
        else:
            issues.append("거래처 사업자번호가 비어 있습니다.")

        if tax_amount != round(supply_amount * 0.1):
            issues.append("세액이 공급가액의 10%와 일치하지 않습니다.")

        lifecycle_state = "validated"
        if raw_issue_status == "발행완료":
            lifecycle_state = "sent"
            issues.append("샘플 데이터: 이미 발행 완료된 행으로 처리됩니다.")
        elif any("사업자번호가 비어" in issue for issue in issues):
            lifecycle_state = "needs-party"
        elif issues:
            lifecycle_state = "failed"
        else:
            lifecycle_state = "ready-to-send"

        records.append(
            {
                "행": f"R-{row_number + 101}",
                "템플릿버전": template_version,
                "거래구분": direction,
                "작성일": issue_date,
                "거래처명": partner_name,
                "거래처사업자번호": business_number,
                "품목": item_name,
                "공급가액": supply_amount,
                "세액": tax_amount,
                "합계금액": total_amount,
                "과세유형": tax_type,
                "상태코드": lifecycle_state,
                "상태": STATUS_LABELS[lifecycle_state],
                "멱등키": idempotency_key,
                "이슈": issues,
            }
        )

    return pd.DataFrame(records)


def summarize_validation(validated: pd.DataFrame) -> dict[str, int]:
    return {
        "ready-to-send": int((validated["상태코드"] == "ready-to-send").sum()),
        "needs-party": int((validated["상태코드"] == "needs-party").sum()),
        "failed": int((validated["상태코드"] == "failed").sum()),
        "sent": int((validated["상태코드"] == "sent").sum()),
    }
