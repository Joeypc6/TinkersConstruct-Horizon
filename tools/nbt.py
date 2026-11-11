"""A small reader of Minecraft's NBT (a gzipped structure file): compounds as dicts, lists as lists."""
import gzip
import struct


def read(data):
    """The root compound of `data` (gzipped or not)."""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    at = [0]

    def take(n):
        b = data[at[0]:at[0] + n]
        at[0] += n
        return b

    def string():
        (n,) = struct.unpack(">H", take(2))
        return take(n).decode("utf-8", "replace")

    def value(kind):
        if kind == 1:
            return struct.unpack(">b", take(1))[0]
        if kind == 2:
            return struct.unpack(">h", take(2))[0]
        if kind == 3:
            return struct.unpack(">i", take(4))[0]
        if kind == 4:
            return struct.unpack(">q", take(8))[0]
        if kind == 5:
            return struct.unpack(">f", take(4))[0]
        if kind == 6:
            return struct.unpack(">d", take(8))[0]
        if kind == 7:
            (n,) = struct.unpack(">i", take(4))
            return list(take(n))
        if kind == 8:
            return string()
        if kind == 9:
            inner = take(1)[0]
            (n,) = struct.unpack(">i", take(4))
            return [value(inner) for _ in range(n)]
        if kind == 10:
            out = {}
            while True:
                k = take(1)[0]
                if k == 0:
                    return out
                name = string()
                out[name] = value(k)
        if kind == 11:
            (n,) = struct.unpack(">i", take(4))
            return list(struct.unpack(f">{n}i", take(4 * n)))
        if kind == 12:
            (n,) = struct.unpack(">i", take(4))
            return list(struct.unpack(f">{n}q", take(8 * n)))
        raise ValueError(f"NBT tag {kind}")

    kind = take(1)[0]
    string()
    return value(kind)


def structure_blocks(data):
    """A structure file's blocks as [x, y, z, id, {property: value}] (air left out)."""
    root = read(data)
    palette = root.get("palette") or (root.get("palettes") or [[]])[0]
    out = []
    for b in root.get("blocks", []):
        state = palette[b["state"]]
        name = state.get("Name", "minecraft:air")
        if name.endswith(":air") or name == "minecraft:structure_void":
            continue
        x, y, z = b["pos"]
        out.append([x, y, z, name, dict(state.get("Properties", {}))])
    return out
