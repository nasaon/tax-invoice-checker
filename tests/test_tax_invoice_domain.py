import json
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pandas as pd

from tax_invoice_domain import TEMPLATE_VERSION, make_self_test_template, summarize_validation, validate_rows
from tax_invoice_records import IssuanceLedger, LocalSampleFileStore
from tax_invoice_adapters import LocalFormatVerifier, NtsPublicApiVerifier, QueuePreviewAdapter


class TaxInvoiceDomainTest(unittest.TestCase):
    def test_valid_row_becomes_ready_to_send(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "스튜디오 모루",
                    "거래처사업자번호": "214-81-33210",
                    "품목": "디자인 용역",
                    "공급가액": 300000,
                    "세액": 30000,
                    "과세유형": "과세",
                    "발행상태": "",
                }
            ]
        )

        validated = validate_rows(source)

        self.assertEqual(validated.iloc[0]["상태코드"], "ready-to-send")

    def test_missing_business_number_becomes_needs_party(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매입",
                    "작성일": "2026-05-12",
                    "거래처명": "퍼플 미디어",
                    "거래처사업자번호": "",
                    "품목": "광고 집행비",
                    "공급가액": 500000,
                    "세액": 50000,
                    "과세유형": "과세",
                    "발행상태": "",
                }
            ]
        )

        validated = validate_rows(source)

        self.assertEqual(validated.iloc[0]["상태코드"], "needs-party")

    def test_already_issued_row_becomes_sent(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "오후 다섯시",
                    "거래처사업자번호": "318-04-77111",
                    "품목": "행사 운영비",
                    "공급가액": 700000,
                    "세액": 70000,
                    "과세유형": "과세",
                    "발행상태": "발행완료",
                }
            ]
        )

        validated = validate_rows(source)

        self.assertEqual(validated.iloc[0]["상태코드"], "sent")


    def test_invalid_business_number_format_becomes_failed(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "플로우 커머스",
                    "거래처사업자번호": "1234567890",
                    "품목": "디자인 용역",
                    "공급가액": 300000,
                    "세액": 30000,
                    "과세유형": "과세",
                    "발행상태": "",
                }
            ]
        )

        validated = validate_rows(source)

        self.assertEqual(validated.iloc[0]["상태코드"], "failed")


class TaxInvoiceQueueTest(unittest.TestCase):
    def test_queue_preview_adapter_returns_standard_queued_result(self) -> None:
        row = pd.Series(
            {
                "행": "R-101",
                "거래처명": "스튜디오 모루",
                "상태코드": "ready-to-send",
            }
        )

        result = QueuePreviewAdapter().preview_issue(row)

        self.assertEqual(result.queue_state, "queued")
        self.assertEqual(result.message, "실제 발행 대신 발행 큐 생성만 수행합니다.")
        self.assertIsNone(result.external_id)

    def test_queue_preview_adapter_rejects_non_ready_row(self) -> None:
        row = pd.Series(
            {
                "행": "R-103",
                "거래처명": "플로우 커머스",
                "상태코드": "failed",
            }
        )

        result = QueuePreviewAdapter().preview_issue(row)

        self.assertEqual(result.queue_state, "rejected")
        self.assertEqual(result.message, "발행 대기 상태의 행만 큐 미리보기를 생성할 수 있습니다.")
        self.assertIsNone(result.external_id)

    def test_duplicate_idempotency_key_becomes_duplicate_blocked(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "스튜디오 모루",
                    "거래처사업자번호": "214-81-33210",
                    "품목": "디자인 용역",
                    "공급가액": 300000,
                    "세액": 30000,
                    "과세유형": "과세",
                    "발행상태": "",
                },
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "스튜디오 모루",
                    "거래처사업자번호": "214-81-33210",
                    "품목": "디자인 용역",
                    "공급가액": 300000,
                    "세액": 30000,
                    "과세유형": "과세",
                    "발행상태": "",
                },
            ]
        )

        validated = validate_rows(source)
        queue = IssuanceLedger().prepare_queue(validated, QueuePreviewAdapter())

        self.assertEqual(queue.iloc[0]["큐상태"], "queued")
        self.assertEqual(queue.iloc[1]["큐상태"], "duplicate-blocked")

    def test_sample_batch_is_saved_to_local_files(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "템플릿버전": TEMPLATE_VERSION,
                    "거래구분": "매출",
                    "작성일": "2026-05-12",
                    "거래처명": "스튜디오 모루",
                    "거래처사업자번호": "214-81-33210",
                    "품목": "디자인 용역",
                    "공급가액": 300000,
                    "세액": 30000,
                    "과세유형": "과세",
                    "발행상태": "",
                }
            ]
        )

        validated = validate_rows(source)
        queue = IssuanceLedger().prepare_queue(validated, QueuePreviewAdapter())

        with TemporaryDirectory() as temp_dir:
            artifacts = LocalSampleFileStore(base_dir=temp_dir).save_batch(
                validated,
                queue,
                "unit-test",
            )

            self.assertTrue(artifacts.validation_csv.exists())
            self.assertTrue(artifacts.queue_csv.exists())
            self.assertTrue(artifacts.audit_json.exists())

    def test_100_row_self_test_has_zero_error_rate(self) -> None:
        validated = validate_rows(make_self_test_template(100))
        summary = summarize_validation(validated)
        queue = IssuanceLedger().prepare_queue(validated, QueuePreviewAdapter())

        self.assertEqual(summary["ready-to-send"], 100)
        self.assertEqual(summary["needs-party"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["sent"], 0)
        self.assertTrue((queue["큐상태"] == "queued").all())

    def test_saved_audit_json_reports_zero_error_rate_for_self_test(self) -> None:
        validated = validate_rows(make_self_test_template(100))
        queue = IssuanceLedger().prepare_queue(validated, QueuePreviewAdapter())

        with TemporaryDirectory() as temp_dir:
            artifacts = LocalSampleFileStore(base_dir=temp_dir).save_batch(
                validated,
                queue,
                "self-test",
            )

            audit_payload = json.loads(artifacts.audit_json.read_text(encoding="utf-8"))

            self.assertEqual(audit_payload["validated_rows"], 100)
            self.assertEqual(audit_payload["queue_state_counts"]["queued"], 100)


class BusinessNumberVerifierTest(unittest.TestCase):
    def test_local_format_verifier_accepts_valid_format(self) -> None:
        result = LocalFormatVerifier().verify("214-81-33210")

        self.assertTrue(result.is_registered)
        self.assertIsNone(result.reason)

    def test_local_format_verifier_rejects_invalid_format(self) -> None:
        result = LocalFormatVerifier().verify("1234567890")

        self.assertFalse(result.is_registered)
        self.assertIsNotNone(result.reason)

    def test_nts_api_verifier_returns_valid_for_registered_number(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status_code": "OK",
            "data": [{"b_no": "1168100276", "b_stt": "계속사업자", "b_stt_cd": "01",
                      "tax_type": "일반과세자", "tax_type_cd": "01"}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("tax_invoice_adapters.requests.post", return_value=mock_response):
            result = NtsPublicApiVerifier(service_key="test-key").verify("116-81-00276")

        self.assertTrue(result.is_registered)

    def test_nts_api_verifier_returns_invalid_for_unregistered_number(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status_code": "OK",
            "data": [{"b_no": "0000000000", "b_stt": "", "b_stt_cd": "",
                      "tax_type": "국세청에 등록되지 않은 사업자등록번호입니다.", "tax_type_cd": ""}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("tax_invoice_adapters.requests.post", return_value=mock_response):
            result = NtsPublicApiVerifier(service_key="test-key").verify("000-00-00000")

        self.assertFalse(result.is_registered)
        self.assertIsNotNone(result.reason)


if __name__ == "__main__":
    unittest.main()
