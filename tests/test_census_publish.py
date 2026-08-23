import unittest

from scripts.census_publish import duplicate_issues, issue_title, pick_existing_issue


class TestIssueTitle(unittest.TestCase):
    def test_uses_the_exact_pinned_format(self):
        self.assertEqual(issue_title("pocket-draft"), "▶ Resume here — pocket-draft")


class TestPickExistingIssue(unittest.TestCase):
    def test_finds_the_open_issue_with_the_matching_title(self):
        # Arrange
        issues = [
            {"number": 4, "title": "Something else", "state": "open"},
            {"number": 7, "title": "▶ Resume here — pocket-draft", "state": "open"},
        ]
        # Act
        result = pick_existing_issue(issues, "pocket-draft")
        # Assert
        self.assertEqual(result, 7)

    def test_reopens_a_closed_resume_issue_rather_than_creating_a_second(self):
        issues = [{"number": 7, "title": "▶ Resume here — pocket-draft", "state": "closed"}]
        self.assertEqual(pick_existing_issue(issues, "pocket-draft"), 7)

    def test_returns_none_when_no_resume_issue_exists(self):
        issues = [{"number": 4, "title": "Something else", "state": "open"}]
        self.assertIsNone(pick_existing_issue(issues, "pocket-draft"))

    def test_does_not_match_another_repos_resume_issue(self):
        issues = [{"number": 7, "title": "▶ Resume here — knowflow", "state": "open"}]
        self.assertIsNone(pick_existing_issue(issues, "pocket-draft"))


class TestDuplicateHandling(unittest.TestCase):
    def test_picks_the_oldest_issue_when_the_create_list_race_made_two(self):
        # Arrange
        issues = [
            {"number": 3, "title": "▶ Resume here — pocket-draft", "state": "open"},
            {"number": 2, "title": "▶ Resume here — pocket-draft", "state": "open"},
        ]
        # Act
        result = pick_existing_issue(issues, "pocket-draft")
        # Assert
        self.assertEqual(result, 2)

    def test_reports_the_open_duplicates_to_close(self):
        issues = [
            {"number": 3, "title": "▶ Resume here — pocket-draft", "state": "open"},
            {"number": 2, "title": "▶ Resume here — pocket-draft", "state": "open"},
            {"number": 1, "title": "Something else", "state": "open"},
        ]
        self.assertEqual(duplicate_issues(issues, "pocket-draft", keep=2), [3])

    def test_already_closed_duplicates_are_left_alone(self):
        issues = [
            {"number": 3, "title": "▶ Resume here — pocket-draft", "state": "closed"},
            {"number": 2, "title": "▶ Resume here — pocket-draft", "state": "open"},
        ]
        self.assertEqual(duplicate_issues(issues, "pocket-draft", keep=2), [])


if __name__ == "__main__":
    unittest.main()
