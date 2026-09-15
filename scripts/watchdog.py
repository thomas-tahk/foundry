#!/usr/bin/env python3
"""Notice when a watched job stops running, and say so in Discord.

Every other signal the factory produces is delivered by something that is
itself on a schedule — the inbox file the phone reads, the digest the evening
message carries. When the schedule is what broke, those channels go quiet, and
a quiet channel looks exactly like a channel with nothing to report. This is
the one check that lives outside the thing it watches.

It asks the runner, not the app: has this workflow finished successfully inside
its window? That question stays answerable however the job failed — dropped by
GitHub, erroring on every run, or removed by accident.

Auth: GITHUB_TOKEN (cross-repo read), DISCORD_WEBHOOK_URL (where to say it).
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_report import OWNER, gh

HUB_ROOT = Path(__file__).resolve().parent.parent
WATCHED_FILE = HUB_ROOT / "watched.txt"
STATE_FILE = HUB_ROOT / "watch" / "state.json"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")


def load_watched():
    """Read watched.txt into (repo, workflow, hours) triples."""
    if not WATCHED_FILE.exists():
        return []

    watched = []
    for line in WATCHED_FILE.read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) != 3:
            continue
        repo, workflow, hours = fields
        watched.append((repo, workflow, int(hours)))
    return watched


def last_success(repo, workflow):
    """When the workflow last finished successfully, or None if it never has."""
    runs = gh(
        f"/repos/{OWNER}/{repo}/actions/workflows/{workflow}/runs",
        {"status": "success", "per_page": 1},
    )
    if not isinstance(runs, dict):
        return None

    recent = runs.get("workflow_runs") or []
    if not recent:
        return None
    return datetime.fromisoformat(recent[0]["updated_at"].replace("Z", "+00:00"))


# A job with no successful run at all is a different fact from a job that has
# gone quiet, and inventing an hour count for it would be a made-up number.
NEVER = -1


def hours_silent(repo, workflow, window, now):
    """Hours since the job last succeeded, or None while it is inside `window`.

    NEVER when it has never finished successfully — a fresh workflow, a renamed
    file, a deleted one.
    """
    succeeded_at = last_success(repo, workflow)
    if succeeded_at is None:
        return NEVER

    silent = (now - succeeded_at).total_seconds() / 3600
    return round(silent) if silent > window else None


def alarm_text(repo, workflow, silent):
    ran = (
        "has never finished successfully"
        if silent == NEVER
        else f"has not run successfully in {silent} hours"
    )
    return (
        f"🔴 **{repo} has gone quiet.** `{workflow}` {ran}.\n"
        f"Nothing it normally sends will arrive until it runs again — "
        f"<https://github.com/{OWNER}/{repo}/actions/workflows/{workflow}>"
    )


def recovery_text(repo, workflow):
    return f"✅ **{repo} is running again.** `{workflow}` finished successfully."


def post(message):
    """Send one message to the Discord channel. Returns True if it landed.

    The webhook is a credential: only the response status is ever printed.
    """
    if not WEBHOOK:
        print("  ! DISCORD_WEBHOOK_URL is not set; nothing can be said.")
        return False

    body = json.dumps({"content": message}).encode()
    req = urllib.request.Request(WEBHOOK, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as err:
        print(f"  ! Discord refused the post -> HTTP {err.code}")
        return False
    except Exception as err:  # noqa: BLE001 - a watchdog must not crash
        print(f"  ! Discord post failed -> {type(err).__name__}")
        return False


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text()).get("firing", {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(firing):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"firing": firing}, indent=2, sort_keys=True) + "\n")


def main():
    now = datetime.now(timezone.utc)
    was_firing = load_state()
    firing = {}

    for repo, workflow, window in load_watched():
        key = f"{repo}/{workflow}"
        silent = hours_silent(repo, workflow, window, now)

        if silent is None:
            print(f"  ok  {key}")
            # Only the transition is worth a message. An alarm repeated every
            # hour becomes the noise it was meant to cut through.
            if key in was_firing:
                post(recovery_text(repo, workflow))
            continue

        print(f"  !!  {key} — {'never succeeded' if silent == NEVER else f'silent {silent}h'}")
        firing[key] = now.isoformat(timespec="seconds")
        if key not in was_firing:
            post(alarm_text(repo, workflow, silent))
        else:
            firing[key] = was_firing[key]

    save_state(firing)


if __name__ == "__main__":
    main()
