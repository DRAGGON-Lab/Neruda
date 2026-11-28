"""Generate the starter's synthetic coordinate-scaling figure and receipt."""

import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import tempfile
import zlib


GENERATOR = Path(__file__).resolve()
PROJECT = GENERATOR.parents[2]
DATA = GENERATOR.with_name("scaling.json")
OUTPUT = PROJECT / "src/figures/generated/coordinate-scaling.png"
RECEIPT = OUTPUT.with_suffix(".receipt.json")
WIDTH, HEIGHT = 254, 204
GRID = 38


def png_chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data)))


def plot(start, end):
    pixels = bytearray(b"\xff" * (WIDTH * HEIGHT * 3))

    def horizontal(left, right, row, color):
        offset = (row * WIDTH + left) * 3
        length = right - left + 1
        pixels[offset:offset + length * 3] = color * length

    origin_x, origin_y = 32, 180
    grid_color = bytes.fromhex("dce3eb")
    axis_color = bytes.fromhex("263b51")
    point_color = bytes.fromhex("18548a")
    for x in range(6):
        column = origin_x + x * GRID
        for row in range(origin_y - 4 * GRID, origin_y + 1):
            horizontal(column, column, row, grid_color)
    for y in range(5):
        row = origin_y - y * GRID
        horizontal(origin_x, origin_x + 5 * GRID, row, grid_color)
    horizontal(origin_x, origin_x + 5 * GRID + 8, origin_y, axis_color)
    for row in range(origin_y - 4 * GRID - 8, origin_y + 1):
        horizontal(origin_x, origin_x, row, axis_color)

    # The starter scales only the horizontal component.
    left = origin_x + start[0] * GRID
    right = origin_x + end[0] * GRID
    row = origin_y - start[1] * GRID
    for delta in range(-1, 2):
        horizontal(left, right, row + delta, point_color)
    for offset in range(15):
        half_height = (14 - offset) // 2
        column = right - 22 + offset
        for dy in range(-half_height, half_height + 1):
            horizontal(column, column, row + dy, point_color)

    for column in (left, right):
        for dy in range(-7, 8):
            for dx in range(-7, 8):
                radius_squared = dx * dx + dy * dy
                if radius_squared <= 49:
                    color = b"\xff\xff\xff" if column == left and radius_squared <= 16 else point_color
                    horizontal(column + dx, column + dx, row + dy, color)

    stride = WIDTH * 3
    rows = b"".join(b"\0" + pixels[offset:offset + stride]
                    for offset in range(0, len(pixels), stride))
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(rows, level=0)) + png_chunk(b"IEND", b""))


def identity(path, contents):
    return {"path": path.relative_to(PROJECT).as_posix(),
            "sha256": hashlib.sha256(contents).hexdigest()}


def main():
    generator = GENERATOR.read_bytes()
    data = DATA.read_bytes()
    values = json.loads(data)
    start = values["input_cm"]
    scale = values["scale"]
    end = [coordinate * factor for coordinate, factor in zip(start, scale)]
    if (len(start) != 2 or len(scale) != 2
            or any(type(value) is not int for value in start + scale)
            or not 0 < start[0] < end[0] <= 5
            or not 0 < start[1] == end[1] <= 4):
        raise ValueError("expected integer grid coordinates with positive horizontal scaling")
    figure = plot(start, end)
    receipt = {
        "version": 1,
        "generator": identity(GENERATOR, generator),
        "data": identity(DATA, data),
        "runtime": f"{platform.python_implementation()} {platform.python_version()}",
        "output": identity(OUTPUT, figure),
    }

    if OUTPUT.parent.resolve() != OUTPUT.parent:
        raise ValueError("generated figure directory must not use symlinks")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent) as scratch:
        staging = Path(scratch)
        (staging / OUTPUT.name).write_bytes(figure)
        (staging / RECEIPT.name).write_text(json.dumps(receipt, indent=2) + "\n")
        os.replace(staging / OUTPUT.name, OUTPUT)
        os.replace(staging / RECEIPT.name, RECEIPT)
    print(RECEIPT.relative_to(PROJECT))


if __name__ == "__main__":
    main()
