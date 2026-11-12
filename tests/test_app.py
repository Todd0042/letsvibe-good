"""Storage safety and the web API, end to end on a real local server."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import serve  # noqa: E402
from store import BACKUPS_KEPT, Store  # noqa: E402


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.store = Store(self.dir)

    def test_saves_keep_a_limited_number_of_backups_and_no_temp_files(self):
        for n in range(BACKUPS_KEPT + 3):
            self.store.save({"household": f"v{n}", "people": [], "chores": [], "completions": []})
        self.assertEqual(self.store.load()["household"], f"v{BACKUPS_KEPT + 2}")
        self.assertEqual(len(list((self.dir / "backups").iterdir())), BACKUPS_KEPT)
        self.assertEqual(list(self.dir.glob(".fairshare-*.tmp")), [])

    def test_damaged_file_is_restored_from_backup_and_kept(self):
        for name in ("first", "second"):
            self.store.save({"household": name, "people": [], "chores": [], "completions": []})
        self.store.path.write_text("{ not json")
        self.assertEqual(self.store.load()["household"], "first")
        self.assertTrue(self.store.recovered_from)
        self.assertEqual(len(list(self.dir.glob("fairshare.damaged-*.json"))), 1)


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.server = serve(Store(Path(tempfile.mkdtemp())), "127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def post(self, action, body):
        req = urllib.request.Request(f"{self.base}/api/{action}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.load(res)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def setup_home(self):
        return self.post("setup", {"household": "Maple St", "people": ["Alex", "Sam"],
                                   "chores": [{"name": "Dishes", "effort": 1}]})

    def test_setup_needs_two_people_and_explains_why(self):
        status, body = self.post("setup", {"household": "Home", "people": ["Alex"], "chores": [{"name": "Dishes", "effort": 1}]})
        self.assertEqual(status, 400)
        self.assertIn("2", body["error"])

    def test_done_then_undo(self):
        status, body = self.setup_home()
        self.assertEqual(status, 200)
        chore = body["state"]["chores"][0]
        status, body = self.post("done", {"chore_id": chore["id"], "person_id": chore["next"]})
        self.assertEqual(status, 200)
        self.assertIn("is up next", body["message"])
        self.assertEqual(len(body["state"]["history"]), 1)
        status, body = self.post("undo", {})
        self.assertEqual((status, body["state"]["history"]), (200, []))

    def test_bad_input_is_rejected_without_changes(self):
        self.setup_home()
        status, body = self.post("add_chore", {"name": "Mop", "effort": 9})
        self.assertEqual(status, 400)
        self.assertIn("Effort", body["error"])
        status, _ = self.post("add_person", {"name": "x" * 100})
        self.assertEqual(status, 400)
        status, body = self.post("add_person", {"name": "alex"})
        self.assertIn("already", body["error"])

    def test_oversized_request_is_refused(self):
        status, _ = self.post("add_person", {"name": "x" * 20000})
        self.assertEqual(status, 413)

    def test_page_is_served(self):
        with urllib.request.urlopen(f"{self.base}/", timeout=5) as res:
            self.assertIn(b"Fair Share", res.read())


if __name__ == "__main__":
    unittest.main()
