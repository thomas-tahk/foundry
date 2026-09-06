"""Stage 3 is the only step that writes to a project, so its text has to be right."""
import unittest

from scripts.build_publish import pr_body


class PullRequestBody(unittest.TestCase):
    def test_the_attempt_counter_is_hidden_from_the_reader(self):
        body = pr_body({"attempt": 1}, "## What changed\n- a thing")
        self.assertIn("<!-- attempt: 1 -->", body)
        self.assertNotIn("Attempt 1.", body)

    def test_a_retry_says_the_previous_attempt_was_replaced(self):
        body = pr_body({"attempt": 2}, "## What changed\n- a thing")
        self.assertIn("Attempt 2", body)
        self.assertIn("replaced", body)
        self.assertIn("<!-- attempt: 2 -->", body)

    def test_the_counter_survives_a_round_trip_so_the_cap_can_be_enforced(self):
        from scripts.build_facts import attempt_count
        self.assertEqual(attempt_count(pr_body({"attempt": 3}, "body")), 3)
