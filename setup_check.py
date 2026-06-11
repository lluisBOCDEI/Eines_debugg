#!/usr/bin/env python3
"""
Dependency checker and setup helper for ROS2 Data Analyzer
"""

import sys
import subprocess

REQUIRED_PACKAGES = {
    'PyQt5': 'PyQt5.QtWidgets',
    'matplotlib': 'matplotlib',
    'pandas': 'pandas',
    'numpy': 'numpy',
}

OPTIONAL_PACKAGES = {
    'rosbag2_py': 'rosbag2_py',
    'rclpy': 'rclpy',
}

def check_package(name, import_name):
    """Try to import a package."""
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Attempt pip install of a package."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
        return True
    except:
        return False

def main():
    print("=" * 60)
    print("ROS2 Data Analyzer — Dependency Checker")
    print("=" * 60)
    
    print("\n[✓] CHECKING REQUIRED PACKAGES...")
    all_required_ok = True
    for package, import_name in REQUIRED_PACKAGES.items():
        if check_package(package, import_name):
            print(f"  ✓ {package}")
        else:
            print(f"  ✗ {package} — NOT FOUND")
            all_required_ok = False
            print(f"    Installing {package}...")
            if install_package(package):
                print(f"    ✓ {package} installed")
            else:
                print(f"    ✗ Failed to install {package}")
    
    print("\n[✓] CHECKING OPTIONAL PACKAGES...")
    for package, import_name in OPTIONAL_PACKAGES.items():
        if check_package(package, import_name):
            print(f"  ✓ {package}")
        else:
            print(f"  ⚠ {package} — NOT FOUND (needed for bag operations)")
    
    if all_required_ok:
        print("\n" + "=" * 60)
        print("✓ ALL REQUIRED PACKAGES OK!")
        print("=" * 60)
        print("\nYou can now run:")
        print("  python3 ros2_data_analyzer.py")
        return 0
    else:
        print("\n" + "=" * 60)
        print("✗ SOME PACKAGES MISSING")
        print("=" * 60)
        print("\nTry installing with pip:")
        print("  pip install PyQt5 matplotlib pandas numpy rosbag2-py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
