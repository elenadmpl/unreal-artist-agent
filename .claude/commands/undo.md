---
description: Undo everything added since the last checkpoint (with a preview first)
---

I want to undo additions to my level. $ARGUMENTS

1. Run `python tools/ue.py revert-additions` (no --yes!). This is a PREVIEW —
   it lists what would be deleted without touching anything.
2. Show me the list in plain language, grouped ("6 rocks, 2 lights, the
   campfire"), and ask me to confirm.
3. Only after I clearly say yes, run it again with `--yes`, then take a
   screenshot so we both see the result.
4. If there is no checkpoint, say so and offer to take one now
   (`python tools/ue.py snapshot`) so this works next time. Remind me that
   builds via /build always checkpoint automatically first.
5. Never use this to remove things that were in my level before the
   checkpoint — if I ask for that, that's regular editing: confirm exactly
   what I want gone and do it through the editor tools instead.
