from __future__ import annotations

import base64
import hashlib
import os
import re
import sys
from pathlib import Path


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"(?mi)^\s*(?:llm_api_key|LISSAJOUS_LLM_API_KEY)\s*=\s*(['\"])(.+?)\1\s*$",
        text,
    )
    if not match or not match.group(2).strip():
        raise RuntimeError(f"未在 {path} 中找到 llm_api_key。")
    return match.group(2).strip()


def keystream(seed: bytes, size: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < size:
        output.extend(hashlib.sha256(seed + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(output[:size])


def encode_module(api_key: str) -> str:
    plain = api_key.encode("utf-8")
    seed = os.urandom(32)
    mask = os.urandom(32)
    seed_part = bytes(a ^ b for a, b in zip(seed, mask))
    cipher = bytes(a ^ b for a, b in zip(plain, keystream(seed, len(plain))))

    def encoded(value: bytes) -> str:
        return base64.b85encode(value).decode("ascii")

    return f'''from __future__ import annotations

import base64
import hashlib

_A = {encoded(mask)!r}
_B = {encoded(seed_part)!r}
_C = {encoded(cipher)!r}


def reveal_api_key() -> str:
    a = base64.b85decode(_A)
    b = base64.b85decode(_B)
    cipher = base64.b85decode(_C)
    seed = bytes(x ^ y for x, y in zip(a, b))
    stream = bytearray()
    counter = 0
    while len(stream) < len(cipher):
        stream.extend(hashlib.sha256(seed + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(x ^ y for x, y in zip(cipher, stream)).decode("utf-8")
'''


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: encode_secret.py <secrets.toml> <output.py>", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encode_module(read_api_key(source)), encoding="ascii")
    print(f"Embedded API credential generated: {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
