import os
import ast
import pkg_resources
from stdlib_list import stdlib_list

PROJECT_DIR = "."  # Or set to "src" if your code is inside ./src

def get_imports_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return set()
    return {
        node.names[0].name.split('.')[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    }

def get_all_project_imports(root_dir):
    all_imports = set()
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                all_imports.update(get_imports_from_file(os.path.join(subdir, file)))
    return all_imports

def get_requirements_packages(requirements_path="requirements.txt"):
    if not os.path.exists(requirements_path):
        return set()
    with open(requirements_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return {
        pkg_resources.Requirement.parse(line.strip()).name.lower()
        for line in lines
        if line.strip() and not line.startswith("#")
    }

def map_import_to_package(import_name):
    special_cases = {
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "sklearn": "scikit-learn",
        "yaml": "PyYAML",
        "Crypto": "pycryptodome",
        "Image": "Pillow"
    }
    return special_cases.get(import_name, import_name)

# Get standard library modules for current Python version
stdlib_modules = set(stdlib_list("3.13"))

# Run the check
project_imports = get_all_project_imports(PROJECT_DIR)
declared_packages = get_requirements_packages()

missing = []
for imp in project_imports:
    pkg_name = map_import_to_package(imp).lower()
    if pkg_name not in declared_packages and pkg_name not in stdlib_modules:
        missing.append(pkg_name)

if missing:
    print("🚨 Missing packages in requirements.txt:")
    for pkg in sorted(set(missing)):
        print(f"  - {pkg}")
else:
    print("✅ All imports are covered in requirements.txt!")
