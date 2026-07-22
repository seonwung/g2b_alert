import traceback
"""Tests for sanitized HTTP adapter errors."""

import unittest
from unittest.mock import Mock, patch

import requests

from g2b_alert.api.http_client import ApiRequestError, request_json


class ApiErrorSecurityTest(unittest.TestCase):
    def test_http_error_never_exposes_service_key_or_url(self):
        secret = "SECRET-G2B-API-KEY"
        response = Mock(status_code=500)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"500 Server Error for url: https://example.test/api?serviceKey={secret}",
            response=response,
        )

        with patch("g2b_alert.api.http_client.requests.get", return_value=response):
            try:
                request_json(
                    "https://example.test/api",
                    {"serviceKey": secret},
                    30,
                    "테스트 API",
                )
            except ApiRequestError as error:
                rendered = "".join(traceback.format_exception(error))
            else:
                self.fail("ApiRequestError was not raised")

        self.assertNotIn(secret, rendered)
        self.assertNotIn("serviceKey", rendered)
        self.assertIn("HTTP 500", rendered)


if __name__ == "__main__":
    unittest.main()
