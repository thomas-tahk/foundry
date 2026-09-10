"""L3 finds friction mechanically. These cover the thresholds and the shared cap."""
import unittest

from scripts.warm_facts import (
    DEPENDABOT_DAYS,
    default_branch_ci,
    has_friction,
    stale_dependency_prs,
)


class DefaultBranchCI(unittest.TestCase):
    def setUp(self):
        import scripts.warm_facts as module
        self.module = module
        self.original = module.gh
        self.payload = {}
        module.gh = lambda path, params=None: self.payload

    def tearDown(self):
        self.module.gh = self.original

    def test_a_failing_check_is_named(self):
        self.payload = {"check_runs": [
            {"name": "build", "status": "completed", "conclusion": "success"},
            {"name": "test", "status": "completed", "conclusion": "failure"}]}
        result = default_branch_ci("r", "main")
        self.assertEqual(result["state"], "failing")
        self.assertEqual(result["failing"], ["test"])

    def test_a_timeout_counts_as_failing(self):
        self.payload = {"check_runs": [
            {"name": "e2e", "status": "completed", "conclusion": "timed_out"}]}
        self.assertEqual(default_branch_ci("r", "main")["state"], "failing")

    def test_all_green_is_passing(self):
        self.payload = {"check_runs": [
            {"name": "test", "status": "completed", "conclusion": "success"}]}
        self.assertEqual(default_branch_ci("r", "main")["state"], "passing")

    def test_a_running_check_is_not_reported_as_failing(self):
        self.payload = {"check_runs": [
            {"name": "test", "status": "in_progress", "conclusion": None}]}
        self.assertEqual(default_branch_ci("r", "main")["state"], "in_progress")

    def test_a_repo_without_ci_is_not_a_failure(self):
        self.payload = {"check_runs": []}
        self.assertEqual(default_branch_ci("r", "main")["state"], "none")

    def test_a_rerun_that_passed_settles_the_workflow(self):
        """Both runs stay attached to the commit. Only the newest one is the truth."""
        self.payload = {"check_runs": [
            {"name": "tick", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:45:32Z"},
            {"name": "tick", "status": "completed", "conclusion": "success",
             "started_at": "2026-09-08T07:52:07Z"}]}
        self.assertEqual(default_branch_ci("r", "main")["state"], "passing")

    def test_a_rerun_that_failed_is_still_a_failure(self):
        self.payload = {"check_runs": [
            {"name": "tick", "status": "completed", "conclusion": "success",
             "started_at": "2026-09-08T07:45:32Z"},
            {"name": "tick", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:52:07Z"}]}
        result = default_branch_ci("r", "main")
        self.assertEqual(result["state"], "failing")
        self.assertEqual(result["failing"], ["tick"])

    def test_a_failure_says_when_it_started_not_when_it_was_read(self):
        """Stamping this with the read time made the published inbox differ from
        itself every hour, so it was committed every hour."""
        self.payload = {"check_runs": [
            {"name": "build", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:50:00Z"},
            {"name": "tick", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-09T05:00:00Z"}]}
        self.assertEqual(default_branch_ci("r", "main")["failing_since"],
                         "2026-09-08T07:50:00Z")

    def test_a_failure_with_no_start_time_reports_none(self):
        self.payload = {"check_runs": [
            {"name": "build", "status": "completed", "conclusion": "failure"}]}
        self.assertEqual(default_branch_ci("r", "main")["failing_since"], "")

    def test_a_different_workflow_failing_is_not_masked(self):
        self.payload = {"check_runs": [
            {"name": "tick", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:45:32Z"},
            {"name": "tick", "status": "completed", "conclusion": "success",
             "started_at": "2026-09-08T07:52:07Z"},
            {"name": "build", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:50:00Z"}]}
        result = default_branch_ci("r", "main")
        self.assertEqual(result["state"], "failing")
        self.assertEqual(result["failing"], ["build"])

    def test_an_unordered_response_still_picks_the_newest(self):
        self.payload = {"check_runs": [
            {"name": "tick", "status": "completed", "conclusion": "success",
             "started_at": "2026-09-08T07:52:07Z"},
            {"name": "tick", "status": "completed", "conclusion": "failure",
             "started_at": "2026-09-08T07:45:32Z"}]}
        self.assertEqual(default_branch_ci("r", "main")["state"], "passing")


class StaleDependencyPRs(unittest.TestCase):
    def test_an_old_dependabot_pr_is_stale(self):
        prs = [{"head": "dependabot/npm_and_yarn/x", "age_days": DEPENDABOT_DAYS}]
        self.assertEqual(len(stale_dependency_prs(prs)), 1)

    def test_a_fresh_dependabot_pr_is_left_alone(self):
        prs = [{"head": "dependabot/npm_and_yarn/x", "age_days": DEPENDABOT_DAYS - 1}]
        self.assertEqual(stale_dependency_prs(prs), [])

    def test_a_human_branch_is_never_a_dependency_pr(self):
        prs = [{"head": "feat/thing", "age_days": 300}]
        self.assertEqual(stale_dependency_prs(prs), [])


class HasFriction(unittest.TestCase):
    def test_a_warm_repo_has_none(self):
        self.assertFalse(has_friction({"ci": {"state": "passing"},
                                       "stranded_branches": [],
                                       "stale_dependency_prs": []}))

    def test_red_ci_is_friction(self):
        self.assertTrue(has_friction({"ci": {"state": "failing"},
                                      "stranded_branches": [],
                                      "stale_dependency_prs": []}))

    def test_a_stranded_branch_is_friction(self):
        self.assertTrue(has_friction({"ci": {"state": "passing"},
                                      "stranded_branches": [{"name": "feat/x"}],
                                      "stale_dependency_prs": []}))

    def test_a_repo_without_ci_configured_is_not_friction(self):
        self.assertFalse(has_friction({"ci": {"state": "none"},
                                       "stranded_branches": [],
                                       "stale_dependency_prs": []}))


if __name__ == "__main__":
    unittest.main()
