"""Fair Share's web server: the app's pages and a small JSON API (Python standard library only)."""
import json
import sys
import threading
import traceback
import uuid
from dataclasses import asdict
from datetime import date, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from fairness import Chore, Completion, Person, balances, plan, record
from store import Store

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/style.css": ("style.css", "text/css; charset=utf-8")}
MAX_BODY_BYTES = 16 * 1024
MAX_PEOPLE, MAX_CHORES = 20, 50


class InputError(ValueError):
    """A problem the user can fix; the message is shown to them as-is."""


def clean_name(value, what: str) -> str:
    if not isinstance(value, str):
        raise InputError(f"{what} must be text.")
    name = " ".join(value.split())
    if not 1 <= len(name) <= 40:
        raise InputError(f"{what} must be 1 to 40 characters.")
    return name


def clean_effort(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise InputError("Effort must be a whole number from 1 to 5.")
    return value


def find(items: list, item_id, what: str) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    raise InputError(f"That {what} no longer exists. The page has been refreshed.")


def objects(data: dict):
    return ([Person(**p) for p in data["people"]], [Chore(**c) for c in data["chores"]],
            [Completion(**c) for c in data["completions"]])


def add_person(data: dict, name) -> dict:
    name = clean_name(name, "Name")
    if len(data["people"]) >= MAX_PEOPLE:
        raise InputError(f"A home can have up to {MAX_PEOPLE} people.")
    if any(p["name"].lower() == name.lower() for p in data["people"]):
        raise InputError(f"{name} is already in the list.")
    person = asdict(Person(uuid.uuid4().hex[:8], name))
    data["people"].append(person)
    return person


def add_chore(data: dict, name, effort) -> dict:
    name, effort = clean_name(name, "Chore name"), clean_effort(effort)
    if len(data["chores"]) >= MAX_CHORES:
        raise InputError(f"You can track up to {MAX_CHORES} chores.")
    if any(c["name"].lower() == name.lower() for c in data["chores"]):
        raise InputError(f"There is already a chore called {name}.")
    chore = asdict(Chore(uuid.uuid4().hex[:8], name, effort))
    data["chores"].append(chore)
    return chore


# ---- actions: each changes `data` in place and returns the message shown to the user ----------------

def do_setup(data, body, today):
    if data["household"] and data["people"]:
        raise InputError("Fair Share is already set up. Change things in Settings.")
    names, chores = body.get("people"), body.get("chores")
    if not isinstance(names, list) or not 2 <= len(names) <= MAX_PEOPLE:
        raise InputError(f"Add between 2 and {MAX_PEOPLE} people.")
    if not isinstance(chores, list) or not 1 <= len(chores) <= MAX_CHORES or not all(isinstance(c, dict) for c in chores):
        raise InputError(f"Add between 1 and {MAX_CHORES} chores.")
    data.update(household=clean_name(body.get("household"), "Home name"), people=[], chores=[], completions=[])
    for name in names:
        add_person(data, name)
    for c in chores:
        add_chore(data, c.get("name"), c.get("effort"))
    return f"All set! {len(names)} people and {len(chores)} chores. Tap a chore when it's done."


def do_done(data, body, today):
    chore = find(data["chores"], body.get("chore_id"), "chore")
    person = find(data["people"], body.get("person_id"), "person")
    people, _, _ = objects(data)
    data["completions"].append(asdict(record(people, Chore(**chore), person["id"], today)))
    people, chores, completions = objects(data)
    next_id = plan(people, chores, completions, today).get(chore["id"])
    after = f" {find(data['people'], next_id, 'person')['name']} is up next for it." if next_id else ""
    return f"Done! {person['name']} did {chore['name']}.{after}"


def do_undo(data, body, today):
    if not data["completions"]:
        raise InputError("Nothing to undo.")
    last = data["completions"].pop()
    who = next((p["name"] for p in data["people"] if p["id"] == last["person_id"]), "someone")
    return f"Undone: {who} doing {last['chore_name']}."


def do_add_person(data, body, today):
    return f"Added {add_person(data, body.get('name'))['name']}."


def do_remove_person(data, body, today):
    person = find(data["people"], body.get("person_id"), "person")
    if len(data["people"]) <= 2:
        raise InputError("A home needs at least two people to share chores.")
    data["people"].remove(person)
    return f"Removed {person['name']}. Their past chores stay in the history."


def do_set_away(data, body, today):
    person = find(data["people"], body.get("person_id"), "person")
    until = body.get("until")
    if until is None:
        person["away_until"] = None
        return f"Welcome back, {person['name']}!"
    try:
        day = date.fromisoformat(until)
    except (TypeError, ValueError):
        raise InputError("Pick the last day they'll be away.") from None
    if not today <= day <= today + timedelta(days=366):
        raise InputError("Pick a day between today and a year from now.")
    person["away_until"] = day.isoformat()
    return f"{person['name']} is away until {day.isoformat()} and won't be given chores until then."


def do_add_chore(data, body, today):
    return f"Added {add_chore(data, body.get('name'), body.get('effort'))['name']}."


def do_edit_chore(data, body, today):
    chore = find(data["chores"], body.get("chore_id"), "chore")
    chore["effort"] = clean_effort(body.get("effort"))
    return f"{chore['name']} is now effort {chore['effort']}."


def do_remove_chore(data, body, today):
    chore = find(data["chores"], body.get("chore_id"), "chore")
    data["chores"].remove(chore)
    return f"Removed {chore['name']}. It stays in the history."


def do_rename_household(data, body, today):
    data["household"] = clean_name(body.get("household"), "Home name")
    return "Saved the new name."


ACTIONS = {"setup": do_setup, "done": do_done, "undo": do_undo, "add_person": do_add_person,
           "remove_person": do_remove_person, "set_away": do_set_away, "add_chore": do_add_chore,
           "edit_chore": do_edit_chore, "remove_chore": do_remove_chore, "rename_household": do_rename_household}


class FairShare:
    """Runs actions one at a time: load, check, change, save. A failed action never saves."""

    def __init__(self, store: Store):
        self.store, self.lock = store, threading.Lock()

    def view(self) -> dict:
        with self.lock:
            return self._view(self.store.load(), date.today())

    def change(self, action: str, body: dict) -> dict:
        today = date.today()
        with self.lock:
            data = self.store.load()
            message = ACTIONS[action](data, body, today)
            self.store.save(data)
            return {"message": message, "state": self._view(data, today)}

    def _view(self, data: dict, today: date) -> dict:
        people, chores, completions = objects(data)
        bal, nxt = balances(people, completions), plan(people, chores, completions, today)
        names = {p.id: p.name for p in people}
        last = {c.chore_id: c for c in completions}
        return {
            "household": data["household"], "setup_done": bool(data["household"] and people),
            "recovered_from": self.store.recovered_from, "can_undo": bool(completions),
            "people": [{**asdict(p), "balance": bal.get(p.id, 0.0), "away": p.is_away(today)} for p in people],
            "chores": [{**asdict(c), "next": nxt.get(c.id),
                        "last_done": {"by": names.get(last[c.id].person_id, "a former housemate"), "day": last[c.id].day}
                        if c.id in last else None} for c in chores],
            "history": [{"chore": c.chore_name, "by": names.get(c.person_id, "a former housemate"), "day": c.day}
                        for c in reversed(completions[-10:])],
        }


def make_handler(app: FairShare):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FairShare"
        timeout = 10  # a stalled phone connection cannot hold a thread forever

        def log_message(self, fmt, *args):  # keep the console readable; errors are printed below
            pass

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/state":
                return self._json(HTTPStatus.OK, app.view())
            if path in STATIC_FILES:
                name, ctype = STATIC_FILES[path]
                return self._send(HTTPStatus.OK, (STATIC_DIR / name).read_bytes(), ctype)
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

        def do_POST(self):
            action = urlparse(self.path).path.removeprefix("/api/")
            if action not in ACTIONS:
                return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY_BYTES:
                    return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "That request is too large."})
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise InputError("Expected a JSON object.")
                self._json(HTTPStatus.OK, app.change(action, body))
            except InputError as e:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Could not read that request."})
            except Exception:
                traceback.print_exc(file=sys.stderr)
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR,
                           {"error": "Something went wrong saving that. Nothing was changed; please try again."})

        def _json(self, status, payload):
            self._send(status, json.dumps(payload).encode(), "application/json")

        def _send(self, status, body: bytes, ctype: str):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(store: Store, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(FairShare(store)))
    server.daemon_threads = True
    return server
