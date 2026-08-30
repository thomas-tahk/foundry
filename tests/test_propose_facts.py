"""Stage 1 of L1 decides who may be proposed to. These are the guards."""
import unittest

from scripts.propose_facts import (
    _skip_reason,
    extract_source,
    parse_next_steps,
    repo_proposal_state,
)

RESUME_BODY = """## State
Something true.

## Next steps
1. Define the effect type in `engine/types.go` for one card.
2. Draft the bot's deck from the shared pool in `server/carddata.go`.
3. Rebase #1 or close it.

## Blockers
None known.
"""


class ParseNextSteps(unittest.TestCase):
    def test_reads_the_numbered_steps(self):
        steps = parse_next_steps(RESUME_BODY)
        self.assertEqual(len(steps), 3)
        self.assertTrue(steps[0].startswith("Define the effect type"))

    def test_stops_at_the_next_heading(self):
        self.assertNotIn("None known.", parse_next_steps(RESUME_BODY))

    def test_no_section_means_no_steps(self):
        self.assertEqual(parse_next_steps("## State\nNothing else."), [])

    def test_empty_body_is_safe(self):
        self.assertEqual(parse_next_steps(None), [])


class ExtractSource(unittest.TestCase):
    def test_reads_a_plain_source_line(self):
        self.assertEqual(extract_source("body\n\nSource: pocket-draft#4 step 2"),
                         "pocket-draft#4 step 2")

    def test_reads_a_bolded_source_line(self):
        self.assertEqual(extract_source("**Source:** knowflow#16 step 1"),
                         "knowflow#16 step 1")

    def test_absent_source_is_none(self):
        self.assertIsNone(extract_source("no attribution here"))


class SkipReason(unittest.TestCase):
    def test_cap_outranks_everything(self):
        self.assertIn("queue full", _skip_reason(["a step"], True, True))

    def test_missing_resume_issue_is_named(self):
        self.assertIn("no L0 Resume issue", _skip_reason([], False, False))

    def test_resume_without_steps_is_named(self):
        self.assertIn("no next steps", _skip_reason([], False, True))

    def test_eligible_repo_has_no_reason(self):
        self.assertIsNone(_skip_reason(["a step"], False, True))


class RepoProposalState(unittest.TestCase):
    """The eligibility decision, over a stubbed API."""

    def setUp(self):
        self.responses = {}
        import scripts.propose_facts as module
        self.module = module
        self.original = module.gh
        module.gh = lambda path, params=None: self._fake(path, params)

    def tearDown(self):
        self.module.gh = self.original

    def _fake(self, path, params):
        return self.responses.get(params.get("labels") if params else None, [])

    def test_open_steps_under_the_cap_are_eligible(self):
        self.responses = {"factory:resume": [{"number": 7, "body": RESUME_BODY}]}
        state = repo_proposal_state("pocket-draft")
        self.assertTrue(state["eligible"])
        self.assertEqual(state["resume_issue"], 7)
        self.assertEqual(len(state["next_steps"]), 3)

    def test_two_open_proposals_hit_the_cap(self):
        self.responses = {
            "factory:resume": [{"number": 7, "body": RESUME_BODY}],
            "factory:proposed": [{"number": 8, "body": "Source: a"},
                                 {"number": 9, "body": "Source: b"}],
        }
        state = repo_proposal_state("pocket-draft")
        self.assertFalse(state["eligible"])
        self.assertTrue(state["at_cap"])
        self.assertEqual(state["taken_sources"], ["a", "b"])

    def test_declined_sources_are_collected(self):
        self.responses = {
            "factory:resume": [{"number": 7, "body": RESUME_BODY}],
            "factory:declined": [{"number": 3, "body": "Source: pocket-draft#7 step 1"}],
        }
        state = repo_proposal_state("pocket-draft")
        self.assertEqual(state["declined_sources"], ["pocket-draft#7 step 1"])

    def test_pull_requests_never_count_as_proposals(self):
        self.responses = {
            "factory:resume": [{"number": 7, "body": RESUME_BODY}],
            "factory:proposed": [{"number": 8, "body": "Source: a", "pull_request": {}},
                                 {"number": 9, "body": "Source: b", "pull_request": {}}],
        }
        state = repo_proposal_state("pocket-draft")
        self.assertEqual(state["open_proposals"], 0)
        self.assertTrue(state["eligible"])

    def test_no_resume_issue_means_not_eligible(self):
        self.responses = {}
        state = repo_proposal_state("pocket-draft")
        self.assertFalse(state["eligible"])


if __name__ == "__main__":
    unittest.main()
