---
description: Look at the current level and tell me what's in it (and what looks off)
---

Give me a health check of my currently open level. $ARGUMENTS

1. Run `python tools/ue.py scene-report` and `python tools/ue.py screenshot`.
2. Read both, then tell me in plain language:
   - What's in the scene (summarize — "42 rocks, 6 lights, a player start", not a raw list).
   - Anything that looks wrong: things at 0,0,0 that probably shouldn't be, actors
     far away from everything else, duplicates stacked in the same spot, missing
     essentials (no light? no player start?).
3. If I asked about something specific above, focus on that.
4. Suggest at most three improvements, most impactful first. Don't change anything yet.
