"""Stage 1 of the builder decides what gets built, and refuses a fourth attempt."""
import unittest
from datetime import datetime, timezone

from scripts.build_facts import (
    MAX_ATTEMPTS,
    attempt_count,
    build_work,
    buildable,
    has_label,
    slugify,
    summarise_pulls,
)

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)


def pull(number, title, state="open", merged_at=None):
    return {"number": number, "title": title, "state": state, "merged_at": merged_at}


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


class SummarisePulls(unittest.TestCase):
    """What the project already has in flight or shipped recently."""

    def test_an_open_pull_request_is_kept(self):
        summary = summarise_pulls([pull(1, "Add a sticky header")], NOW)
        self.assertEqual(summary, [{"number": 1, "title": "Add a sticky header",
                                    "state": "open"}])

    def test_a_recent_merge_is_kept_with_its_age(self):
        summary = summarise_pulls(
            [pull(2, "Sticky header", state="closed", merged_at="2026-09-01T00:00:00Z")],
            NOW)
        self.assertEqual(summary[0]["state"], "merged")
        self.assertEqual(summary[0]["merged_days_ago"], 7)

    def test_an_old_merge_is_dropped(self):
        summary = summarise_pulls(
            [pull(3, "Ancient work", state="closed", merged_at="2026-01-01T00:00:00Z")],
            NOW)
        self.assertEqual(summary, [])

    def test_a_closed_pull_request_that_never_merged_covers_nothing(self):
        summary = summarise_pulls([pull(4, "Abandoned", state="closed")], NOW)
        self.assertEqual(summary, [])

    def test_nothing_at_all_is_not_an_error(self):
        self.assertEqual(summarise_pulls(None, NOW), [])


class RecentWorkOnHandWrittenTasks(unittest.TestCase):
    """The user cannot know what shipped since they thought of the task."""

    def test_a_task_the_user_typed_carries_what_already_shipped(self):
        work = build_work("priority-post", issue(body="Make the header sticky."),
                          lookup=lambda repo: [{"number": 9, "title": "Sticky header",
                                                "state": "open"}])
        self.assertEqual(work["recent_work"][0]["number"], 9)

    def test_a_proposal_the_factory_wrote_is_checked_against_its_own_evidence(self):
        work = build_work("priority-post",
                          issue(body="Why\n\n<!-- Source: p#2 step 1 -->"),
                          lookup=lambda repo: [{"number": 9, "title": "x",
                                                "state": "open"}])
        self.assertEqual(work["recent_work"], [])

    def test_no_lookup_means_no_recent_work_rather_than_a_missing_field(self):
        work = build_work("priority-post", issue(body="Make the header sticky."))
        self.assertEqual(work["recent_work"], [])
