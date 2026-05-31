import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class InstallerInfo:
    path: str
    name: str
    version: Optional[str]   # no longer used, always None
    size_bytes: int

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / (1024 ** 3), 2)


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def scan_all_installers(extra_paths: Optional[List[str]] = None) -> List[InstallerInfo]:
    installers: List[InstallerInfo] = []

    installers.extend(find_installers_in_applications())

    if extra_paths:
        for p in extra_paths:
            installers.extend(find_installers_in_path(p))

    # Deduplicate by path
    unique = {}
    for inst in installers:
        if inst.path not in unique:
            unique[inst.path] = inst

    return list(unique.values())


# ---------------------------------------------------------
# Discovery (modern macOS only)
# ---------------------------------------------------------

def find_installers_in_applications() -> List[InstallerInfo]:
    apps_dir = "/Applications"
    results = []

    if not os.path.isdir(apps_dir):
        return results

    for entry in os.listdir(apps_dir):
        name = entry.lower()

        # Only detect installers named "Install macOS *.app"
        if not (name.startswith("install macos ") and name.endswith(".app")):
            continue

        full_path = os.path.join(apps_dir, entry)
        info = build_installer_info_from_app(full_path)
        if info:
            results.append(info)

    return results


def find_installers_in_path(path: str) -> List[InstallerInfo]:
    if not os.path.isdir(path):
        return []
    return _scan_directory_for_installers(path)


def _scan_directory_for_installers(root: str) -> List[InstallerInfo]:
    installers: List[InstallerInfo] = []

    for entry in os.scandir(root):
        try:
            if entry.is_dir(follow_symlinks=False):
                name = entry.name.lower()

                if name.startswith("install macos ") and name.endswith(".app"):
                    info = build_installer_info_from_app(entry.path)
                    if info:
                        installers.append(info)
                else:
                    installers.extend(_scan_directory_for_installers(entry.path))

        except PermissionError:
            continue

    return installers


# ---------------------------------------------------------
# Installer info extraction (name + size only)
# ---------------------------------------------------------

def build_installer_info_from_app(path: str) -> Optional[InstallerInfo]:
    # Must contain Info.plist
    info_plist_path = os.path.join(path, "Contents", "Info.plist")
    if not os.path.isfile(info_plist_path):
        return None

    # Extract name from folder name
    bundle_name = os.path.basename(path).replace(".app", "")

    size_bytes = compute_directory_size(path)

    return InstallerInfo(
        path=path,
        name=bundle_name,
        version=None,  # no version parsing anymore
        size_bytes=size_bytes,
    )


# ---------------------------------------------------------
# Size computation
# ---------------------------------------------------------

def compute_directory_size(path: str) -> int:
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                total += os.path.getsize(file_path)
            except OSError:
                continue
    return total
