"""
Saving and loading Fair Share's data safely.

Saves go to a temporary file that replaces the real one only once fully written, so a crash or
power cut can never leave half a file. The previous version is kept as a backup (the last 5 are
kept). If the data file is ever damaged, the newest readable backup is restored and the damaged
file is kept for inspection, never deleted.
"""
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

BACKUPS_KEPT = 5


def empty_data() -> dict:
    return {"version": 1, "household": "", "people": [], "chores": [], "completions": []}


class Store:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.path = self.dir / "fairshare.json"
        self.backups = self.dir / "backups"
        self.backups.mkdir(parents=True, exist_ok=True)
        self.recovered_from: Optional[str] = None  # set when a damaged file was replaced

    def load(self) -> dict:
        if not self.path.exists():
            return empty_data()
        try:
            return self._check(json.loads(self.path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            return self._recover()

    def save(self, data: dict, backup: bool = True) -> None:
        if backup and self.path.exists():
            self._backup()
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".fairshare-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def _backup(self) -> None:
        stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000_000:09d}"
        shutil.copy2(self.path, self.backups / f"fairshare-{stamp}.json")
        for old in sorted(self.backups.glob("fairshare-*.json"))[:-BACKUPS_KEPT]:
            old.unlink(missing_ok=True)

    def _recover(self) -> dict:
        damaged = self.path.with_name(f"fairshare.damaged-{int(time.time())}.json")
        try:
            self.path.replace(damaged)
        except OSError:
            pass
        for candidate in sorted(self.backups.glob("fairshare-*.json"), reverse=True):
            try:
                data = self._check(json.loads(candidate.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                continue
            self.recovered_from = candidate.name
            self.save(data, backup=False)
            return data
        self.recovered_from = "none"
        return empty_data()

    @staticmethod
    def _check(data) -> dict:
        if not isinstance(data, dict) or not all(isinstance(data.get(k), list) for k in ("people", "chores", "completions")):
            raise ValueError("not a Fair Share data file")
        data.setdefault("household", "")
        data.setdefault("version", 1)
        return data
