"""Stage 3 of L1 is the last gate before an issue exists. It re-checks everything."""
import unittest

from scripts.propose_publish import rejection, split_title

STATE = {"at_cap": False, "taken_sources": [], "declined_sources": []}


def state(**overrides):
    return {**STATE, **overrides}


class SplitTitle(unittest.TestCase):
    def test_separates_the_heading_from_the_body(self):
        title, body = split_title("# Add the effect type\n\n**What** — a thing.")
        self.assertEqual(title, "Add the effect type")
        self.assertEqual(body, "**What** — a thing.")

    def test_missing_heading_yields_no_title(self):
        title, body = split_title("**What** — a thing.")
        self.assertIsNone(title)
        self.assertEqual(body, "**What** — a thing.")


class Rejection(unittest.TestCase):
    def test_a_complete_proposal_passes(self):
        self.assertIsNone(rejection("r", "Title", "r#7 step 1", state()))

    def test_a_proposal_without_a_title_is_dropped(self):
        self.assertIn("Title", rejection("r", None, "r#7 step 1", state()))

    def test_a_proposal_without_a_source_is_dropped(self):
        self.assertIn("Source:", rejection("r", "Title", None, state()))

    def test_a_queue_that_filled_since_stage_one_is_respected(self):
        self.assertIn("filled", rejection("r", "Title", "r#7 step 1",
                                          state(at_cap=True)))

    def test_previously_declined_work_is_never_reproposed(self):
        reason = rejection("r", "Title", "r#7 step 1",
                           state(declined_sources=["r#7 step 1"]))
        self.assertIn("declined", reason)

    def test_a_source_with_a_live_proposal_is_dropped(self):
        reason = rejection("r", "Title", "r#7 step 1",
                           state(taken_sources=["r#7 step 1"]))
        self.assertIn("already has an open proposal", reason)

    def test_declined_outranks_taken(self):
        reason = rejection("r", "Title", "r#7 step 1",
                           state(taken_sources=["r#7 step 1"],
                                 declined_sources=["r#7 step 1"]))
        self.assertIn("declined", reason)


if __name__ == "__main__":
    unittest.main()
