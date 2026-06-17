import os
import json
import plistlib
import tempfile
import subprocess
from engine.apple_catalog import fetch_apple_catalog


ICON_MAP = {
    "10.14": "mojave.png",
    "10.15": "catalina.png",
    "11": "bigsur.png",
    "12": "monterey.png",
    "13": "ventura.png",
    "14": "sonoma.png",
    "15": "sequoia.png",
    "26": "tahoe.png",
    
}

TITLE_ICON_MAP = {
    "macOS Mojave": "mojave.png",
    "macOS Catalina": "catalina.png",
    "macOS Big Sur": "bigsur.png",
    "macOS Monterey": "monterey.png",
    "macOS Ventura": "ventura.png",
    "macOS Sonoma": "sonoma.png",
    "macOS Sequoia": "sequoia.png",
    "macoS Tahoe": "tahoe.png",

}


# ---------------------------------------------------------
# Helper: Download .dist metadata using Apple curl
# ---------------------------------------------------------
def download_dist_file(url):
    fd, tmp_path = tempfile.mkstemp(prefix="multimac_dist_", suffix=".dist")
    os.close(fd)

    curl_cmd = [
        "/usr/bin/curl",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--output", tmp_path,
        url
    ]

    result = subprocess.run(
        curl_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to download dist metadata from {url}\n"
            f"stderr:\n{result.stderr}"
        )

    return tmp_path


# ---------------------------------------------------------
# Helper: Parse .dist XML for title/version/build
# ---------------------------------------------------------
def parse_dist_metadata(dist_path):
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(dist_path)
        root = tree.getroot()

        title = root.findtext(".//title")
        version = root.findtext(".//version")
        build = root.findtext(".//build")

        return title, version, build

    except Exception as e:
        raise RuntimeError(f"Failed to parse dist metadata: {e}")


# ---------------------------------------------------------
# Main: Build installer list
# ---------------------------------------------------------
def build_installers(workdir="/tmp/multimac_catalog"):
    os.makedirs(workdir, exist_ok=True)

    catalog_path = os.path.join(workdir, "catalog.plist")
    fetch_apple_catalog(catalog_path)

    with open(catalog_path, "rb") as f:
        catalog = plistlib.load(f)

    products = catalog.get("Products", {})
    installers = []

    for pid, product in products.items():

        # Find InstallAssistant.pkg URL
        pkg_url = None
        pkg_size = None

        for pkg in product.get("Packages", []):
            url = pkg.get("URL", "")
            if url.endswith("InstallAssistant.pkg"):
                pkg_url = url
                pkg_size = pkg.get("Size")
                break

        if not pkg_url:
            continue

        # ---------------------------------------------------------
        # Metadata URL (ServerMetadataURL or Distributions["English"])
        # ---------------------------------------------------------
        metadata_url = (
            product.get("ServerMetadataURL")
            or product.get("Distributions", {}).get("English")
        )

        title = None
        version = None
        build = None
        icon_path = None

        if metadata_url:
            try:
                dist_path = download_dist_file(metadata_url)
                title, version, build = parse_dist_metadata(dist_path)
            except Exception as e:
                print(f"[Catalog] Warning: metadata parse failed for {pid}: {e}")

        # Fallbacks
        title = title or "macOS Installer"
        version = version or "Unknown"
        build = build or "Unknown"

        # ---------------------------------------------------------
        # Icon mapping (version → major)
        # ---------------------------------------------------------
        major = version.split(".")[0]
        icon_file = ICON_MAP.get(major)

        if icon_file:
            icon_path = f"assets/icons/{icon_file}"

        # ---------------------------------------------------------
        # Fallback: icon mapping by title
        # ---------------------------------------------------------
        if icon_path is None and title in TITLE_ICON_MAP:
            icon_path = f"assets/icons/{TITLE_ICON_MAP[title]}"

        identifier = f"{version}-{build}-{pid}"

        installers.append({
            "identifier": identifier,
            "product_id": pid,
            "name": title,
            "version": version,
            "build": build,
            "url": pkg_url,
            "size": pkg_size,
            "icon": icon_path,
        })

    # Dedupe
    seen = set()
    deduped = []
    for i in installers:
        if i["identifier"] not in seen:
            deduped.append(i)
            seen.add(i["identifier"])
    installers = deduped

    # Sort newest → oldest
    installers.sort(
        key=lambda x: (
            x.get("version") or "",
            x.get("build") or "",
        ),
        reverse=True
    )

    print("NEW PIPELINE INSTALLERS:", json.dumps(installers, indent=2))
    return installers
