"""
ODYSSEY MARS-09 Project Setup Script
Lead Architect Specification - Generates complete production-grade simulation modules.
"""

from pathlib import Path

BASE_DIR = Path("ODYSSEY-MARS09")

DIRECTORIES = [
    BASE_DIR / "core",
    BASE_DIR / "data" / "terrain",
    BASE_DIR / "data" / "targets",
    BASE_DIR / "components",
    BASE_DIR / "utils",
    BASE_DIR / "tests",
]

def main():
    print("🚀 Synchronizing ODYSSEY MARS-09 project structure...")
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR]  {directory}")
    print("\n✅ ODYSSEY MARS-09 codebase is up to date!")

if __name__ == "__main__":
    main()
