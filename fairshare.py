#!/usr/bin/env python3
"""
Fair Share: a household chore rotation that is actually fair.

Run:  python fairshare.py            (opens in your browser; phones on the same Wi-Fi can join)
      python fairshare.py --help     (other options)
"""
import argparse
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

if sys.version_info < (3, 9):
    sys.exit("Fair Share needs Python 3.9 or newer. Get it from https://www.python.org/downloads/")

from server import serve  # noqa: E402
from store import Store  # noqa: E402


def default_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "FairShare"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "FairShare"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "fairshare"


def lan_address() -> Optional[str]:
    """This computer's address on the home network. Nothing is sent: a UDP connect only picks a route."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fair Share: a household chore rotation that is actually fair.")
    parser.add_argument("--port", type=int, default=8765, help="port to use (default 8765)")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir(), help="where your data is saved")
    parser.add_argument("--local-only", action="store_true", help="only this computer can open it (no phones)")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser window")
    args = parser.parse_args()

    store = Store(args.data_dir)
    host = "127.0.0.1" if args.local_only else "0.0.0.0"
    try:
        server = serve(store, host, args.port)
    except OSError:
        sys.exit(f"Port {args.port} is already in use. Is Fair Share already running?\n"
                 f"Try another port:  python fairshare.py --port {args.port + 1}")

    local_url = f"http://localhost:{args.port}"
    print("Fair Share is running.")
    print(f"  On this computer:         {local_url}")
    lan = None if args.local_only else lan_address()
    if lan:
        print(f"  On phones (same Wi-Fi):   http://{lan}:{args.port}")
    print(f"  Your data is saved in:    {store.dir}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(local_url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your chores are saved.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
