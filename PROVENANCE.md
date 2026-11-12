# About this repository

This is a **reference project for [LetsVibe](https://letsvibe.todd0042.dev)**, the leaderboard for
vibe-coded software. It anchors the **top** of LetsVibe's grading curve.

- **Written by:** Claude (Anthropic's AI), from a prompt by LetsVibe's creator. It is vibe-coded by
  LetsVibe's own definition: the AI wrote the program.
- **The prompt:** "make a lightweight application for literally anything that satisfies all of the
  aspects in prompts.py and is under 1000 lines of code" (`prompts.py` holds LetsVibe's grading
  criteria).
- **Its counterpart:** [letsvibe-bad](https://github.com/Todd0042/letsvibe-bad), written from the same
  prompt with the adjectives reversed, anchors the bottom.

## Exactly how it was made

- **AI model:** Claude Opus 5.5 (`claude-opus-5-5`), by Anthropic
- **Tool:** Claude Code (Anthropic's coding agent), working in LetsVibe's own repository so it could
  read `letsvibe/evaluator/prompts.py`, the file that defines LetsVibe's grading criteria
- **Date:** 2026-11-11
- **Who prompted it:** Todd0042, LetsVibe's creator. Todd wrote none of the code.

**Prompt for the top anchor (letsvibe-good), in Todd's words:**

> if i were to prompt you "make a lightweight application for literally anything that satisfies all
> of the aspects in prompts.py and is under 1000 lines of code what would you write?

**Prompt for the bottom anchor (letsvibe-bad), in Todd's words:**

> for the bottom just reverse the adjectives - satisfies goes to ignores, etc...

which Claude read as: *"make a heavyweight application for literally anything that ignores all of the
aspects in prompts.py and is under 1000 lines of code"*. The 1000-line limit was kept for both, since
LetsVibe never grades size.

**Other steering, in full:** Todd named the repositories (`letsvibe-good`, `letsvibe-bad`) and asked
for this disclosure. Everything else (the app ideas, names, design and code) was Claude's.

**How the top anchor was built:** Claude first described the app it would write (Fair Share); Todd
said to build it. Claude wrote every file, ran the 14 automated tests, then clicked through the app
in a phone-sized headless browser (setup wizard, marking chores done, undo, settings). That review
found one problem, a date box with no label, which Claude fixed before the first commit. Size:
877 non-blank lines including tests.

Reference projects are used only to calibrate grades. They never appear in LetsVibe's rankings.
Fair Share is also a complete, working app you're welcome to use.
