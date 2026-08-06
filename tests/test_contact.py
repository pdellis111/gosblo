import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

HANDLER_PATH = pathlib.Path(__file__).parents[1] / "infra" / "contact" / "handler.py"
SPEC = importlib.util.spec_from_file_location("contact_handler", HANDLER_PATH)
contact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contact)


class ContactValidationTests(unittest.TestCase):
    def valid_payload(self):
        return {
            "name": "Paul Ellis",
            "email": "paul@example.com",
            "phone": "+61 400 000 000",
            "message": "Please contact me about a systems project.",
            "website": "",
            "startedAt": "1000",
        }

    def test_accepts_valid_payload(self):
        values, error = contact.validate(self.valid_payload(), now_ms=5000)
        self.assertIsNone(error)
        self.assertEqual(values["name"], "Paul Ellis")

    def test_rejects_header_injection_and_invalid_email(self):
        payload = self.valid_payload()
        payload["email"] = "attacker@example.com\nBcc: victim@example.com"
        values, error = contact.validate(payload, now_ms=5000)
        self.assertIsNone(values)
        self.assertEqual(error, "Enter a valid email address.")

    def test_rejects_submission_that_is_too_fast(self):
        values, error = contact.validate(self.valid_payload(), now_ms=2000)
        self.assertIsNone(values)
        self.assertIn("reload", error)

    def test_honeypot_returns_success_without_sending(self):
        payload = self.valid_payload()
        payload["website"] = "https://spam.example"
        event = {"requestContext": {"http": {"method": "POST"}}, "body": json.dumps(payload)}
        with patch.object(contact, "send_email") as sender:
            result = contact.handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        sender.assert_not_called()

    def test_valid_submission_sends_once(self):
        event = {"requestContext": {"http": {"method": "POST"}}, "body": json.dumps(self.valid_payload())}
        with patch.object(contact.time, "time", return_value=5), patch.object(contact, "send_email") as sender:
            result = contact.handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        sender.assert_called_once()

    def test_oversized_request_is_rejected(self):
        event = {"requestContext": {"http": {"method": "POST"}}, "body": "x" * 8193}
        result = contact.handler(event, None)
        self.assertEqual(result["statusCode"], 413)


if __name__ == "__main__":
    unittest.main()
