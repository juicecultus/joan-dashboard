#!/usr/bin/env python3
"""Decode/encode Joan TLV protocol messages.

Frame format (from Configurator traffic analysis):
  [type:1][flags:2][length:1][data:length]

  - flags 0x0000 = read/get
  - flags 0x0001 = write/set
  - data in responses may be raw bytes or ASCII-hex encoded strings
"""

import struct
import sys

KNOWN_TYPES = {
    0x02: "connectivity_type",
    0x0D: "ip_address",
    0x0E: "netmask",
    0x0F: "gateway",
    0x10: "dns",
    0x11: "ip_mode",
    0x12: "server_url",
    0x13: "server_port",
    0x33: "unknown_0x33",
    0x3C: "unknown_0x3C",
    0x3D: "unknown_0x3D",
    0x3E: "unknown_0x3E",
    0x41: "wifi_ssid",
    0x42: "wifi_security",
    0x43: "wifi_psk",
    0x45: "m2m_server",
    0x46: "m2m_field1",
    0x47: "m2m_field2",
    0x48: "m2m_field3",
    0x4A: "unknown_0x4A",
    0x4B: "unknown_0x4B",
    0x4C: "unknown_0x4C",
    0x50: "set_conn_state",
    0x51: "conn_state",
    0x54: "unknown_0x54",
    0x56: "hw_version",
    0x57: "fw_version",
    0x58: "bl_version",
    0x59: "uuid",
    0x6E: "wifi_mac",
    0x81: "unknown_0x81",
    0x90: "unknown_0x90",
}


def decode_tlv(hex_str: str) -> dict:
    """Decode a hex-encoded TLV frame into a dict."""
    raw = bytes.fromhex(hex_str.strip())
    if len(raw) < 4:
        return {"error": "too short", "raw": raw.hex()}

    msg_type = raw[0]
    flags = struct.unpack_from(">H", raw, 1)[0]
    length = raw[3]
    data = raw[4 : 4 + length]

    result = {
        "type": f"0x{msg_type:02X}",
        "type_name": KNOWN_TYPES.get(msg_type, f"unknown_0x{msg_type:02X}"),
        "flags": f"0x{flags:04X}",
        "length": length,
        "data_hex": data.hex(),
    }

    # Try to decode data as ASCII string
    try:
        text = data.decode("ascii")
        if all(32 <= c < 127 for c in data):
            result["data_ascii"] = text
    except Exception:
        pass

    # Try to decode as uint32 LE if length == 4
    if length == 4:
        result["data_u32_le"] = struct.unpack_from("<I", data)[0]
        result["data_u32_be"] = struct.unpack_from(">I", data)[0]

    # Try to decode as uint16 LE if length == 2
    if length == 2:
        result["data_u16_le"] = struct.unpack_from("<H", data)[0]
        result["data_u16_be"] = struct.unpack_from(">H", data)[0]

    return result


def encode_tlv(msg_type: int, data: bytes = b"", flags: int = 0x0000) -> bytes:
    """Encode a TLV frame."""
    header = struct.pack(">BHB", msg_type, flags, len(data))
    return header + data


def encode_tlv_hex(msg_type: int, data: bytes = b"", flags: int = 0x0000) -> str:
    """Encode a TLV frame and return hex string."""
    return encode_tlv(msg_type, data, flags).hex()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: joan_tlv.py <hex_string> [hex_string ...]")
        print("       joan_tlv.py --encode <type_hex> [data_hex] [flags_hex]")
        return 1

    if sys.argv[1] == "--encode":
        msg_type = int(sys.argv[2], 16)
        data = bytes.fromhex(sys.argv[3]) if len(sys.argv) > 3 else b""
        flags = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x0000
        print(encode_tlv_hex(msg_type, data, flags))
        return 0

    for arg in sys.argv[1:]:
        result = decode_tlv(arg)
        for k, v in result.items():
            print(f"  {k}: {v}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
