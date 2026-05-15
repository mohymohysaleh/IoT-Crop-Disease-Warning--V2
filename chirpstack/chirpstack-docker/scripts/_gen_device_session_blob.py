"""Build ChirpStack v4 internal.DeviceSession protobuf blobs (minimal ABP LW1.0.3)."""
from __future__ import annotations


def _varint(n: int) -> bytes:
    out = bytearray()
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)
    return bytes(out)


def _tag(field_no: int, wire_type: int) -> bytes:
    return _varint((field_no << 3) | wire_type)


def _len_delim(field_no: int, payload: bytes) -> bytes:
    return _tag(field_no, 2) + _varint(len(payload)) + payload


def device_session_abp(
    *,
    dev_addr_be: bytes,
    nwk_skey: bytes,
    app_skey: bytes,
    region_config_id: str = "eu868",
    mac_version: int = 3,
) -> bytes:
    """Serialize internal.DeviceSession (api/proto/internal/internal.proto).

    ``dev_addr_be`` must match ``lrwn::DevAddr`` internal / Postgres ``device.dev_addr`` bytes
    (big-endian DevAddr, same as ``encode(dev_addr,'hex')`` in the ChirpStack UI).
    """
    if len(dev_addr_be) != 4 or len(nwk_skey) != 16 or len(app_skey) != 16:
        raise ValueError("dev_addr 4 bytes, keys 16 bytes")

    parts: list[bytes] = []
    # 2 dev_addr
    parts.append(_len_delim(2, dev_addr_be))
    # 4 mac_version (enum, varint)
    parts.append(_tag(4, 0) + _varint(mac_version))
    # 5 f_nwk_s_int_key, 6 s_nwk_s_int_key, 7 nwk_s_enc_key (LW 1.0.x: all NwkSKey)
    parts.append(_len_delim(5, nwk_skey))
    parts.append(_len_delim(6, nwk_skey))
    parts.append(_len_delim(7, nwk_skey))
    # 8 app_s_key (common.KeyEnvelope) — only aes_key for cleartext key
    app_env = _len_delim(2, app_skey)
    parts.append(_len_delim(8, app_env))
    # 40 region_config_id
    rid = region_config_id.encode("utf-8")
    parts.append(_len_delim(40, rid))
    return b"".join(parts)


def main() -> None:
    for node in range(1, 11):
        # Same numeric DevAddr as config/devices.json strings (e.g. "00000001") and nwk_key trailing byte.
        dev_num = node if node < 10 else 0x10  # "00000010" -> 16
        devaddr_be = dev_num.to_bytes(4, "big")
        nwk = bytes(15) + bytes([dev_num])
        app = bytes(16)
        blob = device_session_abp(dev_addr_be=devaddr_be, nwk_skey=nwk, app_skey=app)
        print(f"node={node}", blob.hex())


if __name__ == "__main__":
    main()
