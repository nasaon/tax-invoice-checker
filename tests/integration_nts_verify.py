"""NTS 사업자등록정보 진위확인 API 실제 연동 테스트 (수동 실행용)

실행 전:
  1. cp .env.example .env
  2. .env 파일에 NTS_API_KEY=발급받은키 입력
  3. python tests/integration_nts_verify.py

주의: 이 스크립트는 실제 API를 호출합니다. 단위 테스트가 아닙니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tax_invoice_config import AppConfig
from tax_invoice_adapters import NtsPublicApiVerifier

try:
    config = AppConfig()
except ValueError as exc:
    print(f"❌ 설정 오류: {exc}")
    sys.exit(1)

verifier = NtsPublicApiVerifier(service_key=config.nts_api_key)

TEST_CASES = [
    # (사업자번호, 예상 등록여부, 설명)
    ("000-00-00000", False, "존재하지 않는 번호 → 미등록"),
    ("1234567890",   False, "형식 오류 (하이픈 없음) → LocalFormatVerifier 처리"),
]

MANUAL_CASES = [
    # 직접 사업자번호 입력해서 확인하세요
    # ("XXX-XX-XXXXX", True, "내 사업자번호"),
]

print("=== NTS 사업자번호 진위확인 API 통합 테스트 ===\n")
passed = 0
failed = 0
for bn, expected, desc in TEST_CASES:
    result = verifier.verify(bn)
    ok = result.is_registered == expected
    icon = "✅" if ok else "❌"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{icon} {desc}")
    print(f"   번호: {bn}  →  등록여부: {result.is_registered}  사유: {result.reason}")

if MANUAL_CASES:
    print("\n--- 수동 테스트 ---")
    for bn, expected, desc in MANUAL_CASES:
        result = verifier.verify(bn)
        ok = result.is_registered == expected
        icon = "✅" if ok else "❌"
        print(f"{icon} {desc}  →  등록여부: {result.is_registered}")

print(f"\n자동 결과: {passed}건 통과 / {failed}건 실패")
print("\n💡 내 사업자번호 확인:")
print("   MANUAL_CASES에 ('XXX-XX-XXXXX', True, '내 사업자번호') 추가 후 재실행하세요.")

