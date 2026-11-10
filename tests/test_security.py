"""Security behavior tests for API key handling."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tax_invoice_config import AppConfig, SecretStr
from tax_invoice_adapters import NtsPublicApiVerifier


class SecretStrTest(unittest.TestCase):
    def test_repr_does_not_expose_value(self) -> None:
        secret = SecretStr("super-secret-key-12345")

        self.assertNotIn("super-secret-key-12345", repr(secret))
        self.assertNotIn("super-secret-key-12345", str(secret))

    def test_get_secret_value_returns_actual_value(self) -> None:
        secret = SecretStr("actual-value")

        self.assertEqual(secret.get_secret_value(), "actual-value")

    def test_secret_not_leaked_in_exception_context(self) -> None:
        secret = SecretStr("leak-me-not")
        container = {"key": secret}

        self.assertNotIn("leak-me-not", str(container))


class AppConfigTest(unittest.TestCase):
    def test_raises_when_nts_key_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NTS_API_KEY", None)
            with self.assertRaises(ValueError) as ctx:
                AppConfig(env_file="/nonexistent/.env.test")
            self.assertIn("NTS_API_KEY", str(ctx.exception))

    def test_raises_when_nts_key_is_placeholder(self) -> None:
        with patch.dict(os.environ, {"NTS_API_KEY": "여기에_발급받은_인증키_입력"}):
            with self.assertRaises(ValueError):
                AppConfig(env_file="/nonexistent/.env.test")

    def test_loads_nts_key_as_secret_str(self) -> None:
        with patch.dict(os.environ, {"NTS_API_KEY": "real-key-abc"}):
            config = AppConfig()

        self.assertIsInstance(config.nts_api_key, SecretStr)
        self.assertEqual(config.nts_api_key.get_secret_value(), "real-key-abc")


class NtsVerifierSecurityTest(unittest.TestCase):
    def test_repr_does_not_expose_service_key(self) -> None:
        verifier = NtsPublicApiVerifier(service_key="my-secret-key")

        self.assertNotIn("my-secret-key", repr(verifier))

    def test_api_call_passes_service_key_as_query_param(self) -> None:
        """data.go.kr API는 serviceKey 쿼리 파라미터를 요구합니다 (헤더 미지원 — API 제약)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b_no": "2148133210", "valid": "01", "valid_msg": ""}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("tax_invoice_adapters.requests.post", return_value=mock_response) as mock_post:
            NtsPublicApiVerifier(service_key="my-secret-key").verify("214-81-33210")

        call_kwargs = mock_post.call_args
        params = call_kwargs.kwargs.get("params") or {}
        self.assertIn("serviceKey", params)
        self.assertEqual(params["serviceKey"], "my-secret-key")


if __name__ == "__main__":
    unittest.main()
