import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Resolve resource paths for:
      - PyInstaller ONEFILE (_MEIPASS)
      - PyInstaller ONEDIR macOS (Contents/Resources)
      - Running from source
    """

    # ONEFILE mode
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    # ONEDIR macOS bundle
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        bundle_dir = os.path.dirname(sys.executable)
        resources = os.path.abspath(os.path.join(bundle_dir, "..", "Resources"))
        return os.path.join(resources, relative_path)

    # Running from source
    return os.path.join(os.path.abspath("."), relative_path)

