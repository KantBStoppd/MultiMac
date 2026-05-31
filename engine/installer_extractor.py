import os
import shutil
import subprocess
from pathlib import Path

class InstallerExtractor:
    def __init__(self, logger=print):
        self.log = logger

    def extract(self, pkg_path, output_dir="/Applications"):
        pkg_path = Path(pkg_path)
        work_dir = pkg_path.parent / "expanded_pkg"
        extract_dir = pkg_path.parent / "extracted_app"

        # Clean old dirs
        if work_dir.exists():
            shutil.rmtree(work_dir)
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        self.log(f"[Extractor] Expanding pkg: {pkg_path}")
        subprocess.run([
            "pkgutil", "--expand-full",
            str(pkg_path),
            str(work_dir)
        ], check=True)

        # Locate Payload
        payload = None
        for root, dirs, files in os.walk(work_dir):
            if "Payload" in files:
                payload = Path(root) / "Payload"
                break

        if not payload:
            raise RuntimeError("Payload not found in expanded pkg")

        self.log(f"[Extractor] Found Payload: {payload}")

        extract_dir.mkdir(parents=True, exist_ok=True)

        self.log(f"[Extractor] Extracting Payload...")
        subprocess.run([
            "tar", "-xf",
            str(payload),
            "-C", str(extract_dir)
        ], check=True)

        # Locate .app
        installer_app = None
        for root, dirs, files in os.walk(extract_dir):
            for d in dirs:
                if d.startswith("Install macOS") and d.endswith(".app"):
                    installer_app = Path(root) / d
                    break

        if not installer_app:
            raise RuntimeError("Installer .app not found after extraction")

        self.log(f"[Extractor] Found installer app: {installer_app}")

        # Move to /Applications
        final_path = Path(output_dir) / installer_app.name

        if final_path.exists():
            shutil.rmtree(final_path)

        shutil.move(str(installer_app), str(final_path))

        self.log(f"[Extractor] Installed to: {final_path}")

        return str(final_path)
