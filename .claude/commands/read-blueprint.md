---
description: Read a Blueprint and explain it in plain language (e.g. /read-blueprint BP_Door)
---

I want to understand a Blueprint: $ARGUMENTS

1. If I didn't name one above, run `python tools/ue.py list-blueprints` and show me
   a short, friendly list to pick from — group by folder, guess what each one is
   from its name.
2. Run `python tools/ue.py read-blueprint <the one I want>`.
3. Read the generated report in `exports/blueprints/` and explain it to me the way
   you'd explain it to an artist who has never opened a Blueprint:
   - What kind of thing is it?
   - When does it do things (events), and what does it do (calls)?
   - Which settings (variables) are safe and interesting for me to tweak?
   - Be honest about anything the report couldn't see.
4. End by offering one concrete thing we could change together.
