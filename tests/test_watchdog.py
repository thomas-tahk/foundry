"""The one check that survives the schedule breaking. Its job is to be loud."""
from datetime import datetime, timedelta, timezone

from scripts.watchdog import NEVER, alarm_text, hours_silent, load_watched

NOW = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)


def at(hours_ago):
    return NOW - timedelta(hours=hours_ago)


class TestHoursSilent:
    def test_a_job_inside_its_window_is_quiet_for_a_good_reason(self, monkeypatch):
        monkeypatch.setattr("scripts.watchdog.last_success", lambda r, w: at(4))

        assert hours_silent("priority-post", "tick.yml", 30, NOW) is None

    def test_a_job_past_its_window_reports_total_silence_not_overshoot(self, monkeypatch):
        # "seven hours late" understates a job that has been dead for a day and
        # a half. The number a person needs is how long nothing has arrived.
        monkeypatch.setattr("scripts.watchdog.last_success", lambda r, w: at(37))

        assert hours_silent("priority-post", "tick.yml", 30, NOW) == 37

    def test_the_boundary_itself_is_still_fine(self, monkeypatch):
        # Exactly at the window, nothing is wrong yet. A job that runs every
        # thirty hours should not alarm every thirty hours.
        monkeypatch.setattr("scripts.watchdog.last_success", lambda r, w: at(30))

        assert hours_silent("priority-post", "tick.yml", 30, NOW) is None

    def test_a_job_that_never_succeeded_is_not_given_an_invented_hour_count(self, monkeypatch):
        # A workflow that has never run is a different fact from one that has
        # gone quiet, and the window is not a measurement of it.
        monkeypatch.setattr("scripts.watchdog.last_success", lambda r, w: None)

        assert hours_silent("priority-post", "tick.yml", 30, NOW) == NEVER


class TestWatchedFile:
    def test_it_reads_the_shipped_list(self):
        watched = load_watched()

        assert ("priority-post", "tick.yml", 30) in watched

    def test_comments_and_blank_lines_are_ignored(self, tmp_path, monkeypatch):
        listing = tmp_path / "watched.txt"
        listing.write_text("# a note\n\nknowflow  keepalive.yml  26\n")
        monkeypatch.setattr("scripts.watchdog.WATCHED_FILE", listing)

        assert load_watched() == [("knowflow", "keepalive.yml", 26)]


class TestAlarmText:
    def test_it_names_how_long_nothing_has_arrived(self):
        text = alarm_text("priority-post", "tick.yml", 37)

        assert "37 hours" in text
        assert "priority-post" in text

    def test_a_job_that_never_ran_is_described_that_way(self):
        text = alarm_text("priority-post", "tick.yml", NEVER)

        assert "never finished successfully" in text
        assert "-1" not in text
