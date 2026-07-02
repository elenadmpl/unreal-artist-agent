"""uasset_peek.py — look inside a .uasset file WITHOUT opening Unreal.

.uasset files are binary, but they start with a table of every name the
asset uses: classes, functions, variables, and the other assets it points
at. This tool digs that table out so you can answer "what IS this file and
what does it depend on?" from a plain terminal.

    python tools/ue.py peek "MyProject/Content/Blueprints/BP_Door.uasset"

Best effort by design: Epic changes the format between engine versions, so
when the structured read fails we fall back to scanning for readable
strings. For the full picture (graphs, variables, defaults) use
`ue.py read-blueprint`, which asks the running editor instead.
"""

import os
import re
import struct
import sys

PACKAGE_MAGIC = 0x9E2A83C1
MAX_FILE_BYTES = 200 * 1024 * 1024


def _read_fstring(buf, off):
    """Read one length-prefixed Unreal string. Raises ValueError if implausible."""
    if off + 4 > len(buf):
        raise ValueError("truncated")
    (length,) = struct.unpack_from("<i", buf, off)
    off += 4
    if length == 0:
        return "", off
    if length > 0:
        if length > 65536 or off + length > len(buf):
            raise ValueError("implausible ascii length")
        raw = buf[off:off + length]
        off += length
        text = raw.rstrip(b"\x00").decode("ascii")
    else:
        count = -length
        if count > 65536 or off + 2 * count > len(buf):
            raise ValueError("implausible utf16 length")
        raw = buf[off:off + 2 * count]
        off += 2 * count
        text = raw.decode("utf-16-le").rstrip("\x00")
    if any(ord(ch) < 32 for ch in text):
        raise ValueError("control characters")
    return text, off


def _summary_name_table(buf):
    """Try the structured route: parse the package summary to find the name table."""
    try:
        return _summary_name_table_inner(buf)
    except (ValueError, struct.error):
        return None


def _summary_name_table_inner(buf):
    if len(buf) < 64:
        return None
    (magic,) = struct.unpack_from("<I", buf, 0)
    if magic != PACKAGE_MAGIC:
        return None
    (legacy,) = struct.unpack_from("<i", buf, 4)
    if not (-10 <= legacy <= -5):
        return None
    off = 8       # LegacyUE3Version
    off += 4      # FileVersionUE4
    off += 4
    if legacy <= -8:
        off += 4  # FileVersionUE5 (UE5+ packages)
    off += 4      # licensee version
    (cv_count,) = struct.unpack_from("<i", buf, off)
    off += 4
    if not (0 <= cv_count < 512):
        return None
    off += cv_count * 20  # custom version entries (guid + int32)
    off += 4              # TotalHeaderSize
    _folder, off = _read_fstring(buf, off)  # FolderName
    off += 4              # PackageFlags
    (name_count,) = struct.unpack_from("<i", buf, off)
    off += 4
    (name_offset,) = struct.unpack_from("<i", buf, off)
    if not (0 < name_count < 2_000_000 and 0 < name_offset < len(buf)):
        return None

    # Modern packages store two 16-bit hashes after each name; old ones don't.
    for hash_bytes in (4, 0):
        names = []
        pos = name_offset
        try:
            for _ in range(name_count):
                text, pos = _read_fstring(buf, pos)
                pos += hash_bytes
                names.append(text)
            return names
        except ValueError:
            continue
    return None


def _scan_strings(buf, minimum=4):
    """Fallback: harvest every plausible length-prefixed string in the file."""
    names, off, end = [], 0, len(buf) - 4
    while off < end:
        try:
            text, new_off = _read_fstring(buf, off)
            if len(text) >= minimum and re.match(r"^[\x20-\x7e -￿]+$", text):
                names.append(text)
                off = new_off
                continue
        except ValueError:
            pass
        off += 1
    return list(dict.fromkeys(names))


def summarize(path):
    size = os.path.getsize(path)
    if size > MAX_FILE_BYTES:
        raise ValueError("File is %d MB - too big to peek safely." % (size // (1024 * 1024)))
    with open(path, "rb") as handle:
        buf = handle.read()

    (magic,) = struct.unpack_from("<I", buf, 0) if len(buf) >= 4 else (0,)
    is_package = magic == PACKAGE_MAGIC

    names = _summary_name_table(buf) if is_package else None
    method = "name table" if names else "string scan (fallback)"
    if not names:
        names = _scan_strings(buf)

    engine_refs = sorted({n for n in names if n.startswith("/Script/")})
    asset_refs = sorted({n for n in names if n.startswith("/Game/") or n.startswith("/Engine/")})
    likely_bp = (
        any(n in ("Blueprint", "WidgetBlueprint", "AnimBlueprint", "BlueprintGeneratedClass") for n in names)
        or any(n.startswith("K2Node") for n in names)
        or any(n.endswith("_C") for n in names)
    )
    other = [n for n in names
             if not n.startswith(("/Script/", "/Game/", "/Engine/"))
             and n not in ("None",)][:80]

    return {
        "file": path,
        "size_bytes": size,
        "valid_unreal_package": is_package,
        "read_method": method,
        "looks_like_blueprint": likely_bp,
        "engine_modules": engine_refs,
        "referenced_assets": asset_refs,
        "names": other,
        "name_count": len(names),
    }


def print_summary(path):
    info = summarize(path)
    print("Peek: %s  (%.1f KB)" % (os.path.basename(info["file"]), info["size_bytes"] / 1024.0))
    if not info["valid_unreal_package"]:
        print("[!] This does not look like an Unreal package (bad magic number).")
        return
    print("Read via: %s   |   Blueprint-like: %s" % (info["read_method"],
                                                     "yes" if info["looks_like_blueprint"] else "no"))
    if info["engine_modules"]:
        print("\nEngine modules it uses:")
        for name in info["engine_modules"][:20]:
            print("  " + name)
    if info["referenced_assets"]:
        print("\nOther assets it points at:")
        for name in info["referenced_assets"][:40]:
            print("  " + name)
    if info["names"]:
        print("\nNames inside (classes, variables, functions...):")
        for name in info["names"]:
            print("  " + name)
    print("\nFor the full graph/variable report, open the project and run:")
    print("  python tools/ue.py read-blueprint <name>")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/uasset_peek.py <file.uasset>")
        sys.exit(1)
    print_summary(sys.argv[1])
