# bump_version.py

import subprocess
import re
import sys

# ---------- CONFIG ----------
DEFAULT_BUMP = "patch"  # or "minor", "major"
# ---------------------------

def get_latest_tag():
    try:
        result = subprocess.run(["git", "tag", "--sort=-creatordate"], capture_output=True, text=True)
        tags = result.stdout.strip().splitlines()
        version_tags = [tag for tag in tags if re.match(r"^v\d+\.\d+\.\d+$", tag)]
        return version_tags[0] if version_tags else "v0.0.0"
    except Exception as e:
        print("❌ Error reading tags:", e)
        sys.exit(1)

def bump_version(version, bump_type):
    major, minor, patch = map(int, version[1:].split("."))
    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = patch = 0
    else:
        raise ValueError("Invalid bump type")
    return f"v{major}.{minor}.{patch}"

def create_tag(new_version):
    message = f"{new_version} – Automated version bump"
    subprocess.run(["git", "tag", "-a", new_version, "-m", message])
    subprocess.run(["git", "push", "origin", new_version])
    print(f"✅ Created and pushed tag: {new_version}")

if __name__ == "__main__":
    bump_type = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUMP
    latest = get_latest_tag()
    next_ver = bump_version(latest, bump_type)
    create_tag(next_ver)
