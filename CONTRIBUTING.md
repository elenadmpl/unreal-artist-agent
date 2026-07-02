# Contributing

Thank you for even opening this file. 💛 This project exists so that artists
and Unreal beginners get a great AI copilot — contributions are judged by one
question: *does this make things easier for someone who can't code?*

## Ways to help (no code required)

- **Report what broke.** You tried the setup and something failed? That's a
  gift — open an issue with what you typed, what you saw, and your UE
  version. `/doctor` output helps a lot.
- **Report what confused you.** If a doc lost you halfway, the doc is wrong,
  not you. Tell us where you stopped understanding.
- **Share results.** A screenshot of something the agent built for you, a
  Blueprint report that was great (or nonsense) — real-world samples drive
  what gets fixed next.

## Ways to help (code)

- **Test coverage against real engine versions.** The in-editor scripts are
  written defensively, but Epic moves things around. Running
  `read-blueprint` on your UE version and reporting what lands in the
  "could NOT see" section is hugely valuable.
- **New readers** (Niagara? animation graphs? sound cues?). The pattern is
  small and consistent — see below.
- **Better reports.** The plain-English generators in `tools/bp_report.py`
  can always explain more things, more kindly.

## The one architectural pattern

Everything that touches Unreal lives in `tools/inside_unreal/` and follows
the same shape:

1. Read arguments from `PARAMS` (injected by `tools/ue.py`; default `{}` so
   the script also runs standalone in the editor via `py path/to/script.py`).
2. Do read-only work, wrapping every engine-version-dependent access in
   `_safe()` / `_prop()` — record what failed in an `errors` list instead of
   crashing.
3. Print the result as JSON between `UAA_RESULT_BEGIN` / `UAA_RESULT_END`
   marker lines.

Then add a subcommand in `tools/ue.py`, and if artists should reach it
directly, a slash command in `.claude/commands/` and a line in `CLAUDE.md`.

## Ground rules

- **Python standard library only** for `tools/` — artists shouldn't need
  `pip install` anything.
- **Reading must stay safe.** Read-tools never modify assets or the level.
  Anything destructive defaults to a dry-run preview and requires an
  explicit `--yes`.
- **All code must be original or MIT-compatible.** Never paste code from
  unlicensed repositories, tutorials without clear licenses, or engine
  source.
- **Plain language in anything user-facing.** If a docs sentence needs
  Unreal jargon, gloss it in parentheses the first time.

## Before you open a PR

```
python tests/test_offline.py     # must print FAILURES: 0
```

CI runs the same suite on Linux + Windows, Python 3.9 and 3.12. If you add
client-side logic (report generators, diffing, parsing), please add a check
to `tests/test_offline.py` — it's a plain script, no framework to learn.
