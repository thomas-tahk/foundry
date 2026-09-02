"""Stage 3 of L1 is the last gate before an issue exists. It re-checks everything."""
import unittest

from scripts.propose_publish import rejection, split_title

STATE = {"at_cap": False, "taken_sources": [], "declined": []}


def declined(*titles):
    return [{"title": t, "source": "r#7 step 1"} for t in titles]


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
        reason = rejection("r", "Add a card effect type", "r#7 step 1",
                           state(declined=declined("Add a card effect type")))
        self.assertIn("declined", reason)

    def test_a_decline_ignores_wording_it_does_not_own(self):
        """Casing and punctuation are not what the user turned down."""
        reason = rejection("r", "Add a Card Effect Type!", "r#7 step 1",
                           state(declined=declined("add a card effect type")))
        self.assertIn("declined", reason)

    def test_a_new_task_at_a_declined_steps_old_number_is_allowed(self):
        """L0 renumbers the Resume issue weekly. The number is not the work.

        Declining "Add a card effect type" at step 2 must not silence whatever
        step 2 becomes next week.
        """
        self.assertIsNone(
            rejection("r", "Draft the bot's deck from the shared pool", "r#7 step 2",
                      state(declined=[{"title": "Add a card effect type",
                                       "source": "r#7 step 2"}])))

    def test_a_different_action_on_a_declined_signal_is_allowed(self):
        """One refusal about a branch does not settle the branch.

        L3 keys on a friction signal; declining "close it" must leave "land it" open.
        """
        self.assertIsNone(
            rejection("r", "Land feat/draft-mode-flow", "r L3 stranded/feat/draft-mode-flow",
                      state(declined=[{"title": "Close feat/draft-mode-flow branch",
                                       "source": "r L3 stranded/feat/draft-mode-flow"}])))

    def test_a_source_with_a_live_proposal_is_dropped(self):
        reason = rejection("r", "Title", "r#7 step 1",
                           state(taken_sources=["r#7 step 1"]))
        self.assertIn("already has an open proposal", reason)

    def test_declined_outranks_taken(self):
        reason = rejection("r", "Title", "r#7 step 1",
                           state(taken_sources=["r#7 step 1"],
                                 declined=declined("Title")))
        self.assertIn("declined", reason)


if __name__ == "__main__":
    unittest.main()
