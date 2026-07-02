# Real-world cities — stream the actual Earth into Unreal

Want to fly over the real Athens, set a scene in real Tokyo, or block out a
shot against the real Manhattan skyline? **Cesium for Unreal** is a free
plugin that streams photorealistic 3D tiles of the whole planet (Google's
Photorealistic 3D Tiles) straight into your level. Once it's set up, the
agent can take you anywhere:

> */real-world Athens at golden hour*
> *"fly me to the Eiffel Tower, 400 meters up"*

## One-time setup (two things only you can do)

### 1. Install the plugin (free, ~2 minutes)
1. Go to [fab.com](https://www.fab.com) (Epic's marketplace), sign in with
   your Epic account.
2. Search **"Cesium for Unreal"** → **Add to Library** → **Install to Engine**.
3. In the editor: **Edit → Plugins** → enable **Cesium for Unreal** → restart.
4. You'll know it worked when **Window → Cesium** exists.

> ⚠️ **Brand-new engine versions:** Fab sometimes lags behind the newest UE
> release ("no compatible engines installed"). If that happens, check the
> [plugin's GitHub releases](https://github.com/CesiumGS/cesium-unreal/releases)
> for a matching build, or use the newest UE version Fab does support.
> Building it from source is possible but is honestly not beginner territory.

### 2. Get a Google Maps API key (~3 minutes)
The photorealistic tiles come from Google, and Google wants to know who's
asking — that's the key. There's a monthly free tier that's plenty for
personal work.

1. [console.cloud.google.com](https://console.cloud.google.com) → create a
   project (any name).
2. Search for **Map Tiles API** → **Enable**.
3. **Credentials → Create credentials → API key** → copy it.

> 🔑 **Two honest warnings.** The key counts usage against *your* Google
> account, so don't publish it. And once a tileset uses it, the key is saved
> **inside your level file** — don't push that project to a public repo.

## Then the agent does the rest

Tell it where you want to go, or run the tool yourself:

```
python tools/ue.py cesium setup --key YOUR_KEY --lat 37.9838 --lon 23.7275
python tools/ue.py cesium goto  --lat 48.8584 --lon 2.2945 --height 400
python tools/ue.py cesium status
```

`setup` creates the three ingredients if they're missing — a
**CesiumGeoreference** (the "where on Earth is my level" anchor), a
**Cesium3DTileset** (the streamed world itself), and a sun + sky so it isn't
pitch black. `goto` moves the anchor and refreshes the tiles. `status` just
looks.

Some coordinates to play with:

| Place | `--lat` | `--lon` | nice `--height` |
|---|---|---|---|
| Athens, Acropolis | 37.9715 | 23.7257 | 300 |
| Paris, Eiffel Tower | 48.8584 | 2.2945 | 400 |
| New York, Times Square | 40.7580 | -73.9855 | 500 |
| Tokyo, Shibuya | 35.6595 | 139.7005 | 400 |
| Santorini | 36.4167 | 25.4333 | 800 |

## Why the tool exists (the trap it avoids)

Moving the world origin looks like "just change the latitude number", but
Cesium only repositions the planet correctly when the change goes through its
*function* (`set_origin_longitude_latitude_height`), not through editing the
property — otherwise tiles render in the wrong place at a weird scale. The
`goto` action always uses the function and then refreshes every tileset.
You get this for free; you just say where you want to go.

## Tips & gotchas

- **Tiles need internet and a few seconds.** A gray or half-loaded world
  right after `goto` is normal — wait, then screenshot.
- **Black screen?** No sun in the level. `setup` adds one; `status` warns you.
- **Performance:** real-world tiles are heavy. Expect them to be the slowest
  thing in your scene; smaller viewport = faster streaming.
- **You can mix worlds:** the streamed city is just an actor — you can place
  your own props, lights, and characters on top of it (see
  [07-BIG-WORLDS.md](07-BIG-WORLDS.md) for making it walkable).
- **Old tutorials mention a free "Cesium ion Google tiles asset"** — that
  route stopped being free; the direct Google key URL this tool uses is the
  current way.
