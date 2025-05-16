import os

EXCLUDE_DIRS = {"venv", "dist", "build", "__pycache__",".git","api"}

def print_tree(root, prefix=""):
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path):
            if name in EXCLUDE_DIRS:
                continue
            print(f"{prefix}📁 {name}")
            print_tree(path, prefix + "    ")
        else:
            print(f"{prefix}📄 {name}")

with open("structure.txt", "w", encoding="utf-8") as f:
    original_stdout = os.sys.stdout
    os.sys.stdout = f
    print_tree(".")
    os.sys.stdout = original_stdout
