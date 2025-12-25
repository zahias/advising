import sys
import os

print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
print(f"sys.path: {sys.path}")

try:
    import utils
    print("Successfully imported utils")
except Exception as e:
    print(f"Failed to import utils: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    import visual_theme
    print("Successfully imported visual_theme")
except Exception as e:
    print(f"Failed to import visual_theme: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
