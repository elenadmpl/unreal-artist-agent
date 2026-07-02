# Your first scene, step by step

You've finished [setup](00-GETTING-STARTED.md) and `/doctor` is green.
Here's a real first session, so you know what to expect.

## 1. Start small — one object

In Claude Code, type:

> place a stone sphere in front of the camera and show me

Watch what the agent does — this is "the loop" you'll see constantly:

1. It calls an Unreal tool to add the sphere (**act**),
2. runs `python tools/ue.py screenshot` (**look**),
3. reads the image and says something like *"the sphere is there but half
   sunk into the floor — fixing"* (**check**),
4. nudges it up and screenshots again (**fix**),
5. then tells you it's done, with the final image saved in `exports/screenshots/`.

If the sphere shows up in your viewport: congratulations, everything works.

## 2. Now something with taste

> Build a small campfire clearing: a dirt circle, a ring of stones, some logs
> to sit on, and warm flickering light like the fire is already burning.
> Evening mood.

Notes for good results:

- **Describe the feeling, not the checklist.** "cozy", "abandoned", "dawn",
  "like a fairy tale" — mood words steer lighting and layout more than exact
  measurements do.
- **Let it finish, then art-direct.** It will do a QA pass on itself. When it
  says done, respond like you would to a junior artist: *"warmer", "the stones
  are too even, scatter them", "pull the camera lower"*.
- **One editor rule:** the agent changes one thing at a time on purpose —
  Unreal only has one brain (game thread), and this keeps it from tripping
  over itself.

## 3. Look at what it sees

Two commands show you the agent's senses:

- `/check-scene` — it lists what's actually in the level and flags oddities
  (things stacked at the same spot, floating objects, missing lights).
- Ask *"show me the level from above"* — it can move the viewpoint, capture,
  and describe.

## 4. Understand something you didn't make

Open any project with Blueprints (a marketplace asset, a template, a friend's
project) and try:

> /read-blueprint

It lists what exists and lets you pick. Then you get the plain-English tour:
what the thing is, when it acts, which settings are yours to play with.
More on this: [02-READING-BLUEPRINTS.md](02-READING-BLUEPRINTS.md).

## 5. Save your work

The agent won't save your level for you unless you ask (saving overwrites
files, and it's careful about that). When you like what you see:
**File → Save All** in Unreal, like always. You can also ask the agent to
save, and it will confirm first.

## If the agent builds something ugly

It happens — same as any artist's first blockout. Iterate. The agent
remembers the conversation, so *"that's too dense, keep the mood but halve
the number of trees"* works. If it gets truly lost: *"undo what you added and
let's start the clearing again"*.
