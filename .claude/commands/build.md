---
description: Build something in the open Unreal level (e.g. /build a cozy campfire clearing)
---

Build this in my currently open Unreal level: $ARGUMENTS

Follow the loop from CLAUDE.md strictly:

1. Restate what you're going to build in one sentence and list the 3-6 steps you
   plan, in plain language. Then start — don't wait for approval unless a step
   would delete or overwrite something of mine.
2. Take a "before" screenshot (`python tools/ue.py screenshot`).
3. Build using the Unreal MCP tools, ONE scene change at a time. If you're unsure
   what tools exist, list/describe the toolsets first.
4. After each visible milestone: screenshot, read the image, and course-correct.
   Check placement numerically with `python tools/ue.py scene-report` when things
   must line up.
5. Finish with an "after" screenshot and tell me, in 2-3 plain sentences, what you
   built and what I might want to ask for next.
