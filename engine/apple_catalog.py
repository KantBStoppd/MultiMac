import os
import subprocess
import tempfile
import shutil

# Mojave-compatible Apple catalog (same one installinstallmacos.py uses)
APPLE_CATALOG_URL = (
    "https://swscan.apple.com/content/catalogs/others/"
    "index-10.15-10.14-10.13-10.12-10.11-10.10-10.9-"
    "mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
)

def fetch_apple_catalog(dest_path):
    """
    Downloads Apple's Mojave-compatible software catalog and saves it to dest_path.
    """

    dest_path = os.path.abspath(dest_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    # Download to temp file first
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="multimac_catalog_", suffix=".plist")
    os.close(tmp_fd)

    curl_cmd = [
        "/usr/bin/curl",          # FORCE Apple curl (MacPorts curl breaks TLS)
        "--fail",
        "--location",
        "--retry", "5",
        "--retry-delay", "2",
        "--retry-max-time", "120",
        "--continue-at", "-",
        "--output", tmp_path,
        "--user-agent", "Mozilla/5.0",
        APPLE_CATALOG_URL,
    ]

    print(f"[Catalog] Fetching Apple catalog:")
    print(f"[Catalog] URL: {APPLE_CATALOG_URL}")

    try:
        result = subprocess.run(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"curl failed with code {result.returncode}\n"
                f"stderr:\n{result.stderr}"
            )

        shutil.move(tmp_path, dest_path)
        print(f"[Catalog] Saved to: {dest_path}")

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

    return dest_path
