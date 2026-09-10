"""The inbox is the only thing priority-post reads. Its shape is a promise."""
from scripts.inbox_publish import (
    build_inbox,
    draft_items,
    failing_build_item,
    proposal_items,
    is_unchanged,
    stranded_items,
    summarize_body,
)

NOW = "2026-09-07T18:00:00Z"


def issue(number, title, created="2026-09-05T14:02:00Z", body=""):
    return {
        "number": number,
        "title": title,
        "created_at": created,
        "body": body,
        "html_url": f"https://github.com/thomas-tahk/priority-post/issues/{number}",
    }


class TestProposals:
    def test_a_proposal_offers_build_and_decline(self):
        items = proposal_items("priority-post", [issue(42, "Add a settings screen")])

        assert len(items) == 1
        item = items[0]
        assert item["state"] == "waiting_on_you"
        assert item["summary"] == "Add a settings screen"
        assert item["repo"] == "thomas-tahk/priority-post"
        assert item["number"] == 42
        keys = [a["key"] for a in item["actions"]]
        assert keys == ["approve", "decline", "read"]

    def test_declining_asks_first_and_approving_does_not(self):
        [item] = proposal_items("priority-post", [issue(42, "Add a settings screen")])
        by_key = {a["key"]: a for a in item["actions"]}

        assert by_key["approve"].get("confirm") is not True
        assert by_key["decline"]["confirm"] is True

    def test_every_label_action_names_the_number_it_writes_to(self):
        [item] = proposal_items("priority-post", [issue(42, "Add a settings screen")])

        for action in item["actions"]:
            if action["kind"] == "apply_label":
                assert action["number"] == 42

    def test_the_issue_body_becomes_the_detail_that_opens(self):
        [item] = proposal_items(
            "priority-post", [issue(42, "Add a settings screen", body="Because the hour is buried in an env var.")]
        )

        assert item["detail"] == "Because the hour is buried in an env var."


class TestDrafts:
    def test_a_retry_writes_its_label_to_the_pull_request_not_the_issue(self):
        pr = {
            "number": 51,
            "title": "Add a settings screen",
            "created_at": "2026-09-06T09:00:00Z",
            "body": "",
            "html_url": "https://github.com/thomas-tahk/priority-post/pull/51",
        }

        [item] = draft_items("priority-post", [pr])

        assert item["state"] == "draft_ready"
        assert item["number"] == 51
        retry = next(a for a in item["actions"] if a["key"] == "retry")
        assert retry["kind"] == "apply_label"
        assert retry["number"] == 51

    def test_review_is_a_link_and_never_a_write(self):
        pr = {"number": 51, "title": "t", "created_at": NOW, "body": "",
              "html_url": "https://github.com/thomas-tahk/priority-post/pull/51"}

        [item] = draft_items("priority-post", [pr])

        review = next(a for a in item["actions"] if a["key"] == "review")
        assert review["kind"] == "open_url"


class TestFrictionHasNoButtons:
    def test_a_failing_build_only_offers_a_link(self):
        item = failing_build_item(
            "knowflow", {"state": "failing", "failing": ["test"]}, "main", "2026-09-01T00:00:00Z"
        )

        assert item["state"] == "build_failing"
        assert item["number"] is None
        assert [a["kind"] for a in item["actions"]] == ["open_url"]

    def test_a_passing_build_produces_nothing(self):
        assert failing_build_item("knowflow", {"state": "passing", "failing": []}, "main", NOW) is None

    def test_a_stranded_branch_only_offers_a_link(self):
        [item] = stranded_items("pocket-draft", [{"name": "feat/x", "ahead_by": 3,
                                                  "last_commit_date": "2026-08-20",
                                                  "age_days": 18}])

        assert item["state"] == "branch_stranded"
        assert [a["kind"] for a in item["actions"]] == ["open_url"]
        assert "12 days" not in item["summary"] and "18 days" in item["summary"]


class TestTheDocument:
    def test_broken_builds_come_first_and_stranded_branches_last(self):
        items = [
            {"state": "branch_stranded", "since": "2026-01-01T00:00:00Z"},
            {"state": "draft_ready", "since": "2026-01-01T00:00:00Z"},
            {"state": "waiting_on_you", "since": "2026-01-01T00:00:00Z"},
            {"state": "build_failing", "since": "2026-01-01T00:00:00Z"},
        ]

        doc = build_inbox(items, NOW)

        assert [i["state"] for i in doc["items"]] == [
            "build_failing", "waiting_on_you", "draft_ready", "branch_stranded"
        ]

    def test_within_a_state_the_thing_waiting_longest_comes_first(self):
        items = [
            {"state": "waiting_on_you", "since": "2026-09-06T00:00:00Z"},
            {"state": "waiting_on_you", "since": "2026-09-01T00:00:00Z"},
        ]

        doc = build_inbox(items, NOW)

        assert [i["since"] for i in doc["items"]] == [
            "2026-09-01T00:00:00Z", "2026-09-06T00:00:00Z"
        ]

    def test_the_document_says_when_it_was_written(self):
        doc = build_inbox([], NOW)

        assert doc["generated_at"] == NOW
        assert doc["items"] == []

    def test_it_carries_the_projects_work_may_be_raised_in(self):
        doc = build_inbox([], NOW, ["pocket-draft", "knowflow"])

        assert doc["projects"] == ["thomas-tahk/pocket-draft", "thomas-tahk/knowflow"]

    def test_electing_nothing_offers_nothing(self):
        assert build_inbox([], NOW)["projects"] == []


class TestTheDetailIsReadable:
    """The detail opens inside a one-line strip on a phone. A proposal body is
    a page of engineering prose; publishing it whole makes the strip unusable."""

    def test_only_the_first_paragraph_survives(self):
        body = "**What** — Draft the bot's deck properly.\n\n**Why now** — Because the preset is fake."

        assert summarize_body(body) == "Draft the bot's deck properly."

    def test_a_long_first_paragraph_is_cut_at_a_word(self):
        body = "word " * 100

        out = summarize_body(body)

        assert len(out) <= 241
        assert out.endswith("…")
        assert not out.endswith("wor…")

    def test_an_empty_body_gives_an_empty_detail(self):
        assert summarize_body("") == ""
        assert summarize_body(None) == ""

    def test_the_published_item_carries_the_short_form(self):
        long_body = "**What** — A short opener.\n\n" + ("filler " * 200)
        [item] = proposal_items("priority-post", [{
            "number": 1, "title": "t", "created_at": "2026-09-01T00:00:00Z",
            "body": long_body, "html_url": "u",
        }])

        assert item["detail"] == "A short opener."


class TestQuietWhenNothingChanged:
    """The inbox refreshes hourly. A commit every hour to say the timestamp
    moved is noise in the log the user reads."""

    def test_the_same_items_at_a_later_time_count_as_unchanged(self):
        old = {"generated_at": "2026-09-07T10:00:00Z", "items": [{"id": "a", "state": "waiting_on_you"}]}
        new = {"generated_at": "2026-09-07T11:00:00Z", "items": [{"id": "a", "state": "waiting_on_you"}]}

        assert is_unchanged(old, new) is True

    def test_a_change_to_any_other_field_counts_as_changed(self):
        old = {"generated_at": "2026-09-07T10:00:00Z", "items": [], "projects": []}
        new = {"generated_at": "2026-09-07T11:00:00Z", "items": [], "projects": ["a"]}

        assert is_unchanged(old, new) is False

    def test_a_new_item_counts_as_changed(self):
        old = {"generated_at": "2026-09-07T10:00:00Z", "items": []}
        new = {"generated_at": "2026-09-07T11:00:00Z", "items": [{"id": "a"}]}

        assert is_unchanged(old, new) is False

    def test_no_previous_file_counts_as_changed(self):
        assert is_unchanged(None, {"generated_at": "x", "items": []}) is False


class TestARedBuildDoesNotRewriteTheFileEveryHour:
    """The bug: the red-build item was stamped with the publish time, so the
    document differed from itself every run and was committed every run."""

    @staticmethod
    def _quiet_repo(monkeypatch, ci):
        from scripts import inbox_publish as mod

        monkeypatch.setattr(mod, "gh", lambda path, params=None: {"default_branch": "main"})
        monkeypatch.setattr(mod, "issues_with_label", lambda *a, **k: [])
        monkeypatch.setattr(mod, "labelled", lambda *a, **k: [])
        monkeypatch.setattr(mod, "live_stranded", lambda *a, **k: [])
        monkeypatch.setattr(mod, "default_branch_ci", lambda *a, **k: ci)
        return mod

    def test_the_same_red_build_reads_the_same_an_hour_later(self, monkeypatch):
        from datetime import datetime, timezone

        mod = self._quiet_repo(monkeypatch, {
            "state": "failing", "failing": ["tick"],
            "failing_since": "2026-09-09T05:00:00Z"})

        first = mod.repo_items("priority-post", datetime(2026, 9, 10, 14, 0, tzinfo=timezone.utc))
        later = mod.repo_items("priority-post", datetime(2026, 9, 10, 18, 0, tzinfo=timezone.utc))

        assert first == later
        assert first[0]["since"] == "2026-09-09T05:00:00Z"

    def test_a_build_that_never_said_when_still_sorts(self, monkeypatch):
        from datetime import datetime, timezone

        mod = self._quiet_repo(monkeypatch, {
            "state": "failing", "failing": ["tick"], "failing_since": ""})

        [item] = mod.repo_items("priority-post", datetime(2026, 9, 10, 18, 0, tzinfo=timezone.utc))

        assert item["since"] == "2026-09-10T18:00:00Z"


class TestNotNowMeansGone:
    """Declining adds a label and removes none. The reader has to filter, or the
    button looks broken: the item you refused comes straight back."""

    @staticmethod
    def labelled_issue(number, *names):
        i = issue(number, f"Proposal {number}")
        i["labels"] = [{"name": n} for n in names]
        return i

    def test_a_declined_proposal_leaves_the_list(self):
        from scripts.inbox_publish import undecided

        kept = undecided([
            self.labelled_issue(4, "factory:proposed", "factory:declined"),
            self.labelled_issue(9, "factory:proposed"),
        ])

        assert [i["number"] for i in kept] == [9]

    def test_a_proposal_already_built_leaves_the_list(self):
        from scripts.inbox_publish import undecided

        kept = undecided([
            self.labelled_issue(9, "factory:proposed", "factory:built"),
            self.labelled_issue(11, "factory:proposed"),
        ])

        assert [i["number"] for i in kept] == [11]

    def test_a_proposal_being_built_right_now_leaves_the_list(self):
        from scripts.inbox_publish import undecided

        kept = undecided([self.labelled_issue(9, "factory:proposed",
                                              "factory:building")])

        assert kept == []

    def test_a_blocked_proposal_leaves_the_list(self):
        from scripts.inbox_publish import undecided

        kept = undecided([self.labelled_issue(9, "factory:proposed",
                                              "factory:blocked")])

        assert kept == []

    def test_an_issue_carrying_no_labels_is_still_undecided(self):
        from scripts.inbox_publish import undecided

        assert len(undecided([issue(11, "Typed by hand")])) == 1
