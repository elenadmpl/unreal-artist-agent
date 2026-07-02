---
description: Stream a real city into Unreal with Cesium (e.g. /real-world Athens at sunset)
---

Bring a real place into my Unreal level: $ARGUMENTS

1. Run `python tools/ue.py cesium status` first.
   - If the Cesium plugin isn't enabled, walk me through installing it (it's free):
     fab.com → search "Cesium for Unreal" → Add to Library → Install to Engine →
     Edit → Plugins → enable → restart. Then check status again.
   - If there's no tileset yet, I need a Google Maps Platform API key (the only
     credential only I can create). Explain it simply: console.cloud.google.com →
     enable "Map Tiles API" → Credentials → Create API key. Warn me kindly that the
     key streams data on my Google account (there's a monthly free tier) and that it
     gets stored inside my level file, so I shouldn't share the project publicly
     with the key in it. Then run
     `python tools/ue.py cesium setup --key <my key> --lat <lat> --lon <lon>`.
2. Work out the latitude/longitude of the place I named yourself (you know the
   coordinates of most cities and landmarks — no need to ask me).
3. If everything is already set up, just move there:
   `python tools/ue.py cesium goto --lat <lat> --lon <lon>` (raise --height for a
   skyline view, ~300-600m for cities).
4. Wait a moment for tiles to stream, then take a screenshot and show me. If the
   screen is black, check the notes the tool printed (usually: no sun in the level).
5. If I asked for a mood ("at sunset", "foggy morning"), art-direct the light AFTER
   the tiles are visible, one change at a time, verifying with screenshots.
