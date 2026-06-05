"""Tests for the email-masking log filter.

Each test pins one realistic way emails sneak into log lines:
literal strings, %s args, multiple emails per record, dict args.
"""
from __future__ import annotations

import io
import logging
import unittest

from cv_critic_agent.security.logging_filter import (
    EmailMaskingFilter,
    install_email_masking,
)


class LoggingFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = logging.getLogger(f"test.{self.id()}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setLevel(logging.DEBUG)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.handler.addFilter(EmailMaskingFilter())
        self.logger.addHandler(self.handler)

    def tearDown(self) -> None:
        self.logger.removeHandler(self.handler)
        self.logger.handlers.clear()

    def out(self) -> str:
        return self.stream.getvalue()

    def test_literal_email_masked(self) -> None:
        self.logger.info("alice@example.com logged in")
        self.assertIn("a****@example.com", self.out())
        self.assertNotIn("alice@", self.out())

    def test_email_in_percent_args_masked(self) -> None:
        self.logger.info("user=%s status=%s", "bob@test.org", "ok")
        self.assertIn("b****@test.org", self.out())
        self.assertNotIn("bob@", self.out())

    def test_multiple_emails_in_one_message(self) -> None:
        self.logger.info("from=alice@a.com to=bob.smith@b.org")
        out = self.out()
        self.assertIn("a****@a.com", out)
        self.assertIn("b****@b.org", out)
        self.assertNotIn("alice@", out)
        self.assertNotIn("bob.smith@", out)

    def test_email_in_dict_args_masked(self) -> None:
        self.logger.info("payload=%(p)s", {"p": "charlie@x.io"})
        self.assertIn("c****@x.io", self.out())
        self.assertNotIn("charlie@", self.out())

    def test_no_email_message_unchanged(self) -> None:
        self.logger.info("hello world 42 not-an-email")
        self.assertIn("hello world 42 not-an-email", self.out())

    def test_at_sign_alone_not_treated_as_email(self) -> None:
        # Things like "@channel" or "rate=10/s @ peak" should not be masked.
        self.logger.info("ping @channel rate=10/s")
        self.assertIn("ping @channel rate=10/s", self.out())

    def test_install_is_idempotent(self) -> None:
        root = logging.getLogger()
        install_email_masking()
        install_email_masking()
        install_email_masking()
        installed = [f for f in root.filters if isinstance(f, EmailMaskingFilter)]
        try:
            self.assertEqual(len(installed), 1)
        finally:
            for f in installed:
                root.removeFilter(f)


if __name__ == "__main__":
    unittest.main()
