import os
import json
import sys
from jsonschema import validate as jsonschema_validate, ValidationError

SCHEMA_MAP = {
    "LifeOSStrategy": "schemas/LifeOSStrategy.schema.json",
    "LifeOSSchema": "schemas/LifeOSSchema.schema.json",
    "LifeOSTree": "schemas/LifeOSTree.schema.json",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON_ROOT = os.path.join(REPO_ROOT, "lifeos", "canon")
MANIFEST_PATH = os.path.join(CANON_ROOT, "Canon_Manifest.json")

class CanonValidationError(Exception):
    pass

class FileMissingError(CanonValidationError):
    pass

class SchemaValidationError(CanonValidationError):
    pass

class IdentityMismatchError(CanonValidationError):
    pass

class OrphanFileError(CanonValidationError):
    pass

class DuplicateEntryError(CanonValidationError):
    pass

def load_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_schema(canon_type):
    if canon_type not in SCHEMA_MAP:
        raise CanonValidationError(f"No schema defined for canon type: {canon_type}")
    schema_path = os.path.join(CANON_ROOT, SCHEMA_MAP[canon_type])
    return load_json(schema_path)

def validate_entry(entry, seen_keys):
    path = os.path.join(CANON_ROOT, entry["path"])
    if not os.path.isfile(path):
        raise FileMissingError(f"Missing file: {entry['path']}")
    data = load_json(path)
    schema = load_schema(entry["type"])
    try:
        jsonschema_validate(instance=data, schema=schema)
    except ValidationError as e:
        raise SchemaValidationError(f"{entry['path']} failed schema validation: {e.message}")
    for field in ("name", "type", "version"):
        if field not in data or data[field] != entry[field]:
            raise IdentityMismatchError(
                f"{entry['path']} field '{field}' mismatch: manifest='{entry[field]}', file='{data.get(field)}'"
            )
    key = (entry["name"], entry["type"])
    if key in seen_keys:
        raise DuplicateEntryError(f"Duplicate canon entry detected: name={entry['name']} type={entry['type']}")
    seen_keys.add(key)

def detect_orphans(manifest_entries):
    referenced_paths = {entry["path"] for entry in manifest_entries}
    subdirs = ["strategies", "schemas", "trees"]
    for subdir in subdirs:
        dir_path = os.path.join(CANON_ROOT, subdir)
        for filename in os.listdir(dir_path):
            if filename.endswith(".json"):
                rel_path = os.path.join(subdir, filename)
                if rel_path not in referenced_paths:
                    raise OrphanFileError(f"Orphan file not registered in manifest: {rel_path}")

def main():
    try:
        manifest = load_manifest()
        entries = manifest.get("entries", [])
        seen_keys = set()
        for entry in entries:
            validate_entry(entry, seen_keys)
        detect_orphans(entries)
        print("✅ Canon validation passed.")
        sys.exit(0)
    except CanonValidationError as e:
        print(f"❌ Canon validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
