import os
import json
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANON_DIR = os.path.join(REPO_ROOT, "lifeos", "canon")
MANIFEST_PATH = os.path.join(CANON_DIR, "Canon_Manifest.json")
TYPES_PATH = os.path.join(CANON_DIR, "CanonTypes.json")

EXT_MAP = {
    "LifeOSStrategy": "strategies",
    "LifeOSSchema": "schemas",
    "LifeOSTree": "trees"
}

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {path}: {e}")
        sys.exit(1)

def main():
    errors = []
    warnings = []

    # Load manifest
    if not os.path.exists(MANIFEST_PATH):
        print(f"[ERROR] Manifest not found at: {MANIFEST_PATH}")
        sys.exit(1)

    manifest = load_json(MANIFEST_PATH)
    if "entries" not in manifest:
        print("[ERROR] Manifest missing 'entries' array.")
        sys.exit(1)

    # Load types (optional)
    valid_types = set()
    if os.path.exists(TYPES_PATH):
        types_json = load_json(TYPES_PATH)
        for entry in types_json.get("types", []):
            if "type" in entry:
                valid_types.add(entry["type"])

    for entry in manifest["entries"]:
        path = entry.get("path")
        typ = entry.get("type")
        name = entry.get("name")
        version = entry.get("version")

        # Check required fields
        if not all([path, typ, name, version]):
            errors.append(f"[ERROR] Missing fields in manifest entry: {entry}")
            continue

        # File existence
        full_path = os.path.join(CANON_DIR, path)
        if not os.path.exists(full_path):
            errors.append(f"[ERROR] Missing file: {path}")
            continue

        # Name must match filename
        file_name = os.path.splitext(os.path.basename(path))[0]
        if file_name != name:
            warnings.append(f"[WARNING] Name mismatch: manifest name '{name}' != filename '{file_name}'")

        # Folder must match declared type
        expected_folder = EXT_MAP.get(typ)
        if expected_folder and not path.startswith(f"{expected_folder}/"):
            errors.append(f"[ERROR] Type-folder mismatch: {typ} should be in '{expected_folder}/' → {path}")

        # Type must be known
        if valid_types and typ not in valid_types:
            warnings.append(f"[WARNING] Unknown type '{typ}' not found in CanonTypes.json")

    # Output summary
    print()
    if errors:
        print("❌ Canon integrity check failed:")
        for e in errors:
            print("-", e)
    else:
        print("✅ No structural errors found in Canon manifest.")

    if warnings:
        print("\n⚠️ Warnings:")
        for w in warnings:
            print("-", w)

    if not errors:
        print(f"\n✔ Canon integrity check passed ({len(manifest['entries'])} entries, {len(warnings)} warnings)")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()