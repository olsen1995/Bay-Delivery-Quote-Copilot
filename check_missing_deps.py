import ast
import os

from stdlib_list import stdlib_list
import pkg_resources


PROJECT_DIR = "."  # Change if needed


def get_local_module_names(root_dir):
    local_modules = set()

    for subdir, dirs, files in os.walk(root_dir):
        if any(part.startswith('.') for part in subdir.split(os.sep)):
            continue  # Skip hidden dirs like .venv, .git

        for file in files:
            if file.endswith(".py"):
                filename = file[:-3]  # remove ".py"
                local_modules.add(filename)

        for d in dirs:
            if not d.startswith(".") and os.path.isfile(os.path.join(subdir, d, "__init__.py")):
                local_modules.add(d)

    return local_modules


def get_imports_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def get_all_project_imports(root_dir):
    all_imports = set()
    exclude_dirs = {".git", ".venv", "__pycache__", "env", "venv", ".mypy_cache", ".pytest_cache"}

    for subdir, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                path = os.path.join(subdir, file)
                try:
                    all_imports.update(get_imports_from_file(path))
                except Exception as e:
                    print(f"⚠️ Skipped {path}: {e}")

    return all_imports


def get_requirements_packages(requirements_path="requirements.txt"):
    if not os.path.exists(requirements_path):
        return set()

    packages = set()

    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                req = pkg_resources.Requirement.parse(line)
                if req.name:
                    packages.add(req.name.lower())
            except Exception:
                continue

    return packages


def map_import_to_package(import_name):
    special_cases = {
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "Image": "Pillow",
        "sklearn": "scikit-learn",
        "yaml": "PyYAML",
        "Crypto": "pycryptodome",
        "dotenv": "python-dotenv",
    }

    return special_cases.get(import_name, import_name)


def main():
    print("\n🔍 Scanning project for missing dependencies...\n")

    stdlib_modules = set(stdlib_list("3.13"))
    local_modules = get_local_module_names(PROJECT_DIR)
    project_imports = get_all_project_imports(PROJECT_DIR)
    declared_packages = get_requirements_packages()

    missing = []

    for imp in project_imports:
        if imp in local_modules:
            continue

        mapped = map_import_to_package(imp)
        if isinstance(mapped, str):
            pkg_name = mapped.lower()
            if pkg_name not in declared_packages and pkg_name not in stdlib_modules:
                missing.append(pkg_name)

    if missing:
        print("🚨 Missing packages in requirements.txt:\n")
        for pkg in sorted(set(missing)):
            print(f"  - {pkg}")
    else:
        print("✅ All imports are covered in requirements.txt!\n")


if __name__ == "__main__":
    main()
