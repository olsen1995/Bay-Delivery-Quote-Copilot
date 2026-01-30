from pathlib import Path
import re

# 1. Fix datetime.UTC usage
memory_file = Path("lifeos/storage/memory_manager.py")
if memory_file.exists():
    content = memory_file.read_text(encoding="utf-8")
    if "datetime.UTC" in content:
        content = re.sub(
            r"datetime\.now\(datetime\.UTC\)",
            "datetime.now(timezone.utc)",
            content
        )
        if "from datetime import datetime" in content and "timezone" not in content:
            content = content.replace(
                "from datetime import datetime",
                "from datetime import datetime, timezone"
            )
        memory_file.write_text(content, encoding="utf-8")
        print("✅ Fixed datetime.UTC in memory_manager.py")
    else:
        print("⏭️ datetime.UTC already fixed or not used.")
else:
    print("⛔ memory_manager.py not found")

# 2. Ensure mode_router is included in main.py
main_file = Path("lifeos/main.py")
if main_file.exists():
    content = main_file.read_text(encoding="utf-8")
    if 'include_router(mode_router' not in content:
        if "from lifeos.routes.mode_router import router as mode_router" not in content:
            content = f"from lifeos.routes.mode_router import router as mode_router\n" + content
        content += "\napp.include_router(mode_router)\n"
        main_file.write_text(content, encoding="utf-8")
        print("✅ Added mode_router to lifeos/main.py")
    else:
        print("⏭️ mode_router already included in main.py")
else:
    print("⛔ main.py not found")

# 3. Set correct headers in test_main.py
test_main = Path("tests/test_main.py")
if test_main.exists():
    content = test_main.read_text(encoding="utf-8")
    if '"x-api-key": "secret123"' not in content:
        content = re.sub(
            r'HEADERS\s*=\s*{[^}]*}',
            'HEADERS = {"x-api-key": "secret123"}',
            content
        )
        test_main.write_text(content, encoding="utf-8")
        print("✅ Set correct x-api-key header in test_main.py")
    else:
        print("⏭️ x-api-key header already correct.")
else:
    print("⛔ test_main.py not found")
