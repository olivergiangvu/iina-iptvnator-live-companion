"""Normalize common PNG channel logos to opaque, black-backed square PNGs.

Pure Python standard library; no Pillow/ImageMagick. Rejects unsupported,
interlaced or excessively large PNGs rather than returning an opaque white tile.
"""
from __future__ import annotations

import binascii
import math
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_SIDE = 2048
MAX_PIXELS = 2_000_000


def _chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", binascii.crc32(payload) & 0xffffffff)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    aa, bb, cc = abs(p - a), abs(p - b), abs(p - c)
    return a if aa <= bb and aa <= cc else b if bb <= cc else c


def flatten_png_black(raw: bytes) -> bytes:
    """Decode noninterlaced 8-bit PNG types 0/2/3/4/6 and square-pad on black.

    Handles indexed 1/2/4/8 bit PNG and tRNS transparency. Unsupported PNGs
    raise ValueError so callers can fall back without inventing artwork.
    """
    if not raw.startswith(SIGNATURE):
        raise ValueError("not PNG")
    offset = len(SIGNATURE)
    ihdr = None
    palette = b""
    transparency = b""
    compressed = []
    while offset + 12 <= len(raw):
        length = struct.unpack_from(">I", raw, offset)[0]
        start = offset + 8
        end = start + length
        if end + 4 > len(raw):
            raise ValueError("PNG truncated")
        typ = raw[offset+4:offset+8]
        blob = raw[start:end]
        if typ == b"IHDR":
            ihdr = blob
        elif typ == b"PLTE":
            palette = blob
        elif typ == b"tRNS":
            transparency = blob
        elif typ == b"IDAT":
            compressed.append(blob)
        elif typ == b"IEND":
            break
        offset = end + 4
    if ihdr is None or len(ihdr) != 13 or not compressed:
        raise ValueError("PNG missing IHDR or image")
    width, height, depth, typ, compression, filtr, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE and width*height <= MAX_PIXELS):
        raise ValueError("PNG dimensions exceed limit")
    channels = {0:1,2:3,3:1,4:2,6:4}.get(typ)
    if channels is None or (depth != 8 and not (typ == 3 and depth in (1,2,4))):
        raise ValueError("unsupported PNG type/depth")
    if compression or filtr or interlace:
        raise ValueError("interlaced or unsupported PNG")
    row_length = (width*channels*depth + 7)//8
    byte_per_pixel = max(1, (channels*depth + 7)//8)
    max_decoded = height*(row_length+1)
    d = zlib.decompressobj()
    decoded = d.decompress(b"".join(compressed), max_decoded+1)
    if len(decoded) != max_decoded or not d.eof:
        raise ValueError("PNG decompression size mismatch")
    if typ == 3 and (len(palette) < 3 or len(palette)%3):
        raise ValueError("PNG missing palette")
    side = max(width, height)
    left = (side-width)//2
    top = (side-height)//2
    out_rows = [b"\x00" + b"\x00"*(side*3) for _ in range(side)]
    pos = 0
    prev = bytearray(row_length)
    for y in range(height):
        filt = decoded[pos]
        pos += 1
        scan = bytearray(decoded[pos:pos+row_length])
        pos += row_length
        if filt not in (0,1,2,3,4):
            raise ValueError("invalid PNG filter")
        for i in range(row_length):
            left_byte = scan[i-byte_per_pixel] if i >= byte_per_pixel else 0
            above = prev[i]
            above_left = prev[i-byte_per_pixel] if i >= byte_per_pixel else 0
            predictor = (0, left_byte, above, (left_byte+above)//2, _paeth(left_byte,above,above_left))[filt]
            scan[i] = (scan[i]+predictor)&255
        prev = scan
        dst = bytearray(out_rows[y+top])
        for x in range(width):
            if typ == 6:
                at = x*4
                r,g,b,a = scan[at:at+4]
            elif typ == 2:
                at = x*3
                r,g,b = scan[at:at+3]
                a = 255
                if len(transparency) >= 6 and bytes([r,g,b]) == bytes(transparency[1:6:2]):
                    a = 0
            elif typ == 4:
                at=x*2
                gray,a = scan[at:at+2]
                r=g=b=gray
            elif typ == 0:
                gray=scan[x]
                r=g=b=gray
                a = 0 if len(transparency)>=2 and gray == transparency[1] else 255
            else:
                value = scan[(x*depth)//8]
                shift = 8-depth-((x*depth)%8)
                idx = (value>>shift) & ((1<<depth)-1)
                if 3*idx+3>len(palette):
                    raise ValueError("PNG palette index invalid")
                r,g,b = palette[3*idx:3*idx+3]
                a = transparency[idx] if idx<len(transparency) else 255
            at = 1+(x+left)*3
            dst[at:at+3] = bytes(((r*a+127)//255, (g*a+127)//255, (b*a+127)//255))
        out_rows[y+top] = bytes(dst)
    out = [SIGNATURE, _chunk(b"IHDR", struct.pack(">IIBBBBB",side,side,8,2,0,0,0))]
    compressor = zlib.compressobj(level=6)
    compressed_out = b"".join(compressor.compress(row) for row in out_rows) + compressor.flush()
    out.append(_chunk(b"IDAT", compressed_out))
    out.append(_chunk(b"IEND",b""))
    return b"".join(out)
