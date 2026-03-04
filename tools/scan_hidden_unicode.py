from pathlib import Path
import unicodedata

FILES = [
    "app/abuse_controls.py",
    "app/main.py",
    "tests/test_abuse_controls.py",
    "tests/test_upload_size_caps.py",
]

BAD_CODEPOINTS = {
    0x202A,0x202B,0x202C,0x202D,0x202E,
    0x2066,0x2067,0x2068,0x2069,
    0x200B,0x200C,0x200D,
    0xFEFF,
    0x2028,0x2029,
}

def scan(fp: str):
    b = Path(fp).read_bytes()
    cr = b.count(b"\r")
    lf = b.count(b"\n")
    text = b.decode("utf-8", errors="replace")
    bad = []
    for i, ch in enumerate(text):
        o = ord(ch)
        cat = unicodedata.category(ch)
        if o in BAD_CODEPOINTS:
            bad.append((i, hex(o), "BAD_CODEPOINT"))
        elif cat == "Cf":
            bad.append((i, hex(o), "FORMAT"))
        elif cat == "Cc" and ch not in ("\n", "\t"):
            bad.append((i, hex(o), "CONTROL"))
    return cr, lf, bad[:10], len(bad)

for fp in FILES:
    cr, lf, sample, count = scan(fp)
    print(fp, "CR", cr, "LF", lf, "bad_count", count, "sample", sample)
    assert count == 0, f"{fp} still has hidden/control chars"

print("OK: no hidden/control chars detected")