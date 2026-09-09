"""Stage 3 is the only step that writes to a project, so its text has to be right."""
import unittest

from scripts.build_publish import finished_labels, pr_body


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


class FinishedLabels(unittest.TestCase):
    """The labels a built issue is left with decide what the inbox says next."""

    def test_it_stops_asking_for_a_decision_already_made(self):
        self.assertIn("factory:proposed", finished_labels()["remove"])

    def test_it_stops_the_next_poll_rebuilding_the_same_work(self):
        self.assertIn("factory:approved", finished_labels()["remove"])

    def test_it_marks_the_issue_built(self):
        self.assertEqual(finished_labels()["add"], ["factory:built"])
