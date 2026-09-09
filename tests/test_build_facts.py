"""Stage 1 of the builder decides what gets built, and refuses a fourth attempt."""
import unittest

from scripts.build_facts import (
    MAX_ATTEMPTS,
    attempt_count,
    build_work,
    buildable,
    has_label,
    slugify,
)


def issue(number=7, title="Score tasks by due date", body="", labels=()):
    return {"number": number, "title": title, "body": body,
            "labels": [{"name": n} for n in labels]}


class Slugify(unittest.TestCase):
    def test_makes_a_branch_safe_fragment(self):
        self.assertEqual(slugify("Score tasks by due date!"),
                         "score-tasks-by-due-date")

    def test_truncates_without_a_trailing_dash(self):
        self.assertEqual(slugify("a" * 30 + " " + "b" * 30, limit=31), "a" * 30)

    def test_a_title_with_no_usable_characters_still_names_something(self):
        self.assertEqual(slugify("!!! ???"), "task")


class AttemptCount(unittest.TestCase):
    def test_an_unmarked_pull_request_is_the_first_attempt(self):
        self.assertEqual(attempt_count("## What changed\n- a thing"), 1)

    def test_the_hidden_marker_is_read_rather_than_the_commit_history(self):
        self.assertEqual(attempt_count("body\n\n<!-- attempt: 2 -->"), 2)

    def test_the_cap_is_reached_at_three(self):
        self.assertGreaterEqual(attempt_count("<!-- attempt: 3 -->"), MAX_ATTEMPTS)


class Labels(unittest.TestCase):
    def test_finds_a_label_it_carries(self):
        self.assertTrue(has_label(issue(labels=["factory:deep"]), "factory:deep"))

    def test_a_missing_item_carries_no_labels(self):
        self.assertFalse(has_label({}, "factory:deep"))


class BuildWork(unittest.TestCase):
    """`premise_cited` is what tells a machine-written task from a hand-written one."""

    def test_a_proposal_the_factory_wrote_is_marked_for_a_premise_check(self):
        work = build_work("priority-post", issue(body="Why\n\n<!-- Source: p#2 step 1 -->"))
        self.assertTrue(work["premise_cited"])

    def test_a_task_the_user_typed_is_not(self):
        work = build_work("priority-post", issue(body="Make the header sticky."))
        self.assertFalse(work["premise_cited"])

    def test_the_branch_names_the_issue_it_came_from(self):
        work = build_work("priority-post", issue(number=12, title="Sticky header"))
        self.assertEqual(work["branch"], "claude/issue-12-sticky-header")

    def test_a_first_build_starts_at_attempt_one_with_no_feedback(self):
        work = build_work("priority-post", issue())
        self.assertEqual(work["attempt"], 1)
        self.assertEqual(work["feedback"], [])


class Buildable(unittest.TestCase):
    """A second tap on a finished task must not spend a run rebuilding it."""

    def test_a_fresh_approved_issue_is_buildable(self):
        self.assertTrue(buildable(issue(labels=["factory:approved"])))

    def test_one_already_being_built_is_not(self):
        self.assertFalse(buildable(issue(labels=["factory:approved",
                                                 "factory:building"])))

    def test_one_already_built_is_not_even_when_approved_again(self):
        self.assertFalse(buildable(issue(labels=["factory:approved",
                                                 "factory:built"])))
