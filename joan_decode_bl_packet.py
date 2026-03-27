#!/usr/bin/env python3
"""Decode the 88-byte bootloader 'Start BL' packet."""

import struct
import sys

# The raw 88-byte packet captured from the bootloader
BL_PACKET_HEX = (
    "020000f000000000b83bfb43ffffffff00000a00"
    "35005a0001504d35523231200000000004000000"
    "0a000000d70a000006000000"
    "0b000000d70f0000"
    "07000000010000000100000001000000"
    "00000000"
    "03000000"
    "99001197"
)


def decode_bl_packet(hex_str: str) -> None:
    raw = bytes.fromhex(hex_str)
    print(f"Total length: {len(raw)} bytes")
    print(f"Full hex: {raw.hex()}")
    print()

    offset = 0

    def read_u8() -> int:
        nonlocal offset
        val = raw[offset]
        offset += 1
        return val

    def read_u16_le() -> int:
        nonlocal offset
        val = struct.unpack_from("<H", raw, offset)[0]
        offset += 2
        return val

    def read_u32_le() -> int:
        nonlocal offset
        val = struct.unpack_from("<I", raw, offset)[0]
        offset += 4
        return val

    def read_bytes(n: int) -> bytes:
        nonlocal offset
        val = raw[offset : offset + n]
        offset += n
        return val

    # Parse header
    pkt_type = read_u8()
    print(f"[0x{0:02X}] Packet type: {pkt_type}")

    # Next 3 bytes — possibly length or flags
    b1, b2, b3 = raw[1], raw[2], raw[3]
    offset = 1
    hdr_rest = read_bytes(3)
    print(f"[0x{1:02X}] Header bytes 1-3: {hdr_rest.hex()} (possibly length={int.from_bytes(hdr_rest, 'little')})")

    # Parse as uint32 fields from offset 4
    offset = 4
    fields = []
    while offset + 4 <= len(raw):
        val = read_u32_le()
        fields.append(val)

    print(f"\nDecoded as {len(fields)} x uint32_le fields from offset 4:")
    for i, val in enumerate(fields):
        off = 4 + i * 4
        raw_bytes = raw[off : off + 4]
        notes = ""

        # Try to identify known values
        if val == 0x43FB3BB8:
            notes = " ← FW CRC"
        elif val == 0xFFFFFFFF:
            notes = " ← HW ID (unset)"
        elif val == 2775:
            notes = " ← FW revision (2775)"
        elif val == 4:
            notes = " ← FW major (4)"
        elif val == 10:
            notes = " ← FW minor (10)"
        elif val == 6:
            notes = " ← BL major (6)"
        elif val == 11:
            notes = " ← BL minor (11)"
        elif val == 4055:
            notes = " ← BL revision (4055)"
        elif val == 7:
            notes = " ← HW name ID (7)"
        elif val == 1 and i > 10:
            notes = " ← (1)"
        elif val == 3:
            notes = " ← PV protocol (3)"
        elif val == 0x97110099:
            notes = " ← Display ID"

        # Check if part of UUID
        if off >= 16 and off < 32:
            notes += f" [UUID region: {raw_bytes.hex()}]"

        print(f"  [{off:3d}] field[{i:2d}] = 0x{val:08X} ({val:10d}) bytes={raw_bytes.hex()}{notes}")

    # Also try parsing UUID at offset 16
    print(f"\n--- UUID region (offset 16, 16 bytes) ---")
    uuid_bytes = raw[16:32]
    print(f"  raw: {uuid_bytes.hex()}")
    # Format as UUID
    uuid_str = "-".join([
        uuid_bytes[0:4].hex().upper(),
        uuid_bytes[4:6].hex().upper(),
        uuid_bytes[6:8].hex().upper(),
        uuid_bytes[8:10].hex().upper(),
        uuid_bytes[10:16].hex().upper(),
    ])
    print(f"  UUID: {uuid_str}")


if __name__ == "__main__":
    hex_input = sys.argv[1] if len(sys.argv) > 1 else BL_PACKET_HEX
    decode_bl_packet(hex_input)
