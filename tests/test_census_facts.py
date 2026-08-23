import unittest
from datetime import datetime, timezone

from scripts.census_facts import (
    age_in_days,
    detect_test_command,
    pick_intent_docs,
    stranded_branches,
)


class TestAgeInDays(unittest.TestCase):
    def test_counts_whole_days_between_iso_timestamps(self):
        # Arrange
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        # Act
        result = age_in_days("2026-08-05T12:00:00Z", now)
        # Assert
        self.assertEqual(result, 7)

    def test_returns_none_for_missing_timestamp(self):
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        self.assertIsNone(age_in_days("", now))


class TestDetectTestCommand(unittest.TestCase):
    def test_go_module_yields_go_test(self):
        self.assertEqual(detect_test_command(["go.mod", "main.go"], {}), "go test ./...")

    def test_package_json_test_script_yields_npm_test(self):
        files = ["package.json"]
        pkg = {"scripts": {"test": "vitest run"}}
        self.assertEqual(detect_test_command(files, pkg), "npm test")

    def test_package_json_without_test_script_yields_none(self):
        self.assertIsNone(detect_test_command(["package.json"], {"scripts": {"dev": "vite"}}))

    def test_no_recognised_manifest_yields_none(self):
        self.assertIsNone(detect_test_command(["README.md"], {}))


class TestPickIntentDocs(unittest.TestCase):
    def test_prefers_vision_and_spec_files_over_incidental_markdown(self):
        # Arrange
        paths = [
            "README.md",
            "docs/VISION.md",
            "docs/superpowers/specs/2026-07-12-draft-mode-full-flow-design.md",
            "node_modules/foo/README.md",
            "docs/adr/0001-go-rules-engine-on-server.md",
        ]
        # Act
        result = pick_intent_docs(paths)
        # Assert
        self.assertIn("README.md", result)
        self.assertIn("docs/VISION.md", result)
        self.assertIn("docs/superpowers/specs/2026-07-12-draft-mode-full-flow-design.md", result)
        self.assertNotIn("node_modules/foo/README.md", result)

    def test_caps_the_list_so_the_prompt_stays_small(self):
        paths = [f"docs/spec-{i}.md" for i in range(50)]
        self.assertLessEqual(len(pick_intent_docs(paths)), 12)


class TestStrandedBranches(unittest.TestCase):
    def test_branch_ahead_with_no_open_pr_is_stranded(self):
        # Arrange
        comparisons = {"feat/x": {"ahead_by": 9, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        # Act
        result = stranded_branches(comparisons, set(), now=now)
        # Assert
        self.assertEqual(result[0]["name"], "feat/x")
        self.assertEqual(result[0]["ahead_by"], 9)
        # 2026-07-14T20:49:32Z → 2026-08-12T00:00:00Z is 28 whole days (28d 3h 10m).
        self.assertEqual(result[0]["age_days"], 28)

    def test_branch_with_an_open_pr_is_not_stranded(self):
        comparisons = {"feat/x": {"ahead_by": 9, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        self.assertEqual(stranded_branches(comparisons, {"feat/x"}, now=now), [])

    def test_branch_not_ahead_is_not_stranded(self):
        comparisons = {"feat/x": {"ahead_by": 0, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        self.assertEqual(stranded_branches(comparisons, set(), now=now), [])


if __name__ == "__main__":
    unittest.main()
