# Fair Share

**A household chore rotation that's actually fair.** Bigger jobs count for more, whoever is furthest
behind is up next, and time away pauses your share instead of piling it up. Everyone in the house
uses it from their phone. No accounts, no cloud, no tracking: your data never leaves your home.

## Quick start

You need **Python 3.9 or newer** ([download](https://www.python.org/downloads/)). Nothing else to install.

| System | How to start |
|---|---|
| Windows | Double-click `start.bat` |
| macOS / Linux | Run `./start.sh` (or `python3 fairshare.py`) |

Fair Share opens in your browser and walks you through a 3-step setup: your home's name, who
lives there, and which chores you share (sensible examples are filled in for you).

**On phones:** the window that starts Fair Share shows an address like `http://192.168.1.20:8765`.
Open it on any phone connected to the same Wi-Fi. If phones can't connect, allow Python through
your computer's firewall when asked.

## Using it

- **Board:** every chore shows who's up next. Tap **"Sam did it"** when it's done, or pick
  "Someone else did it…" if someone else stepped in. Made a mistake? Tap **Undo**.
- **Balances** at the top show who's ahead or behind, in effort points.
- **Settings** (one tap, top right): rename your home, add or remove people and chores, change
  a chore's effort, or mark someone away until a date.

## How it stays fair

Each finished chore earns its effort points (1 = quick, 5 = big job) for whoever did it, and
costs everyone who was home that day an equal share. Your balance is what you earned minus your
share. Next chores go to whoever is furthest behind, biggest jobs first; each suggestion counts
as if it were done, so one person isn't suggested for everything at once. Ties go to whoever did
that chore least recently. People who are away share none of the cost while they're gone.

## Your data

Saved on this computer only (shown when Fair Share starts):

- Windows: `%APPDATA%\FairShare`
- macOS: `~/Library/Application Support/FairShare`
- Linux: `~/.local/share/fairshare`

Every save is written safely (a crash can't leave a half-written file) and the last 5 versions are
kept in `backups/`. If the data file is ever damaged, Fair Share restores the newest backup and
tells you.

Anyone on your home Wi-Fi can open Fair Share, so it's made for a trusted home network. To use
it on this computer only, start it with `--local-only`.

## Options

```
python fairshare.py --port 8766         use another port (if 8765 is taken)
python fairshare.py --local-only        this computer only, no phones
python fairshare.py --no-browser        don't open a browser window
python fairshare.py --data-dir PATH     save data somewhere else
```

## Development

```
python -m unittest discover -s tests
```

`fairness.py` holds the fairness rules (pure functions), `store.py` safe saving and backups,
`server.py` the web server and API, and `static/` the app's screens.

## License

MIT. See [LICENSE](LICENSE).
