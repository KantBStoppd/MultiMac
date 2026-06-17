import os
from engine.installer_scanner import scan_all_installers


# ---------------------------------------------------------
# Minimal, modern InstallerSpec
# ---------------------------------------------------------

class InstallerSpec:
    def __init__(self, name, version, path, size_bytes, size_label, icon=None):
        self.name = name
        self.version = version
        self.path = path
        self.size_bytes = size_bytes
        self.size_label = size_label
        self.icon = icon

    def __repr__(self):
        return f"InstallerSpec(name={self.name!r}, version={self.version!r}, path={self.path!r})"


# ---------------------------------------------------------
# Modern-only installer detection
# ---------------------------------------------------------

def detect_installers():
    """
    Detect macOS installers and normalize names for tile matching.
    """
    installers = scan_all_installers()
    results = []

    for inst in installers:
        raw = inst.name.lower()

        # Normalize names to match UI tiles
        if "sierra" in raw and "high" not in raw:
            name = "Sierra"
        elif "high sierra" in raw:
            name = "High Sierra"
        elif "mojave" in raw:
            name = "Mojave"
        elif "catalina" in raw:
            name = "Catalina"
        elif "big sur" in raw:
            name = "Big Sur"
        elif "monterey" in raw:
            name = "Monterey"
        elif "ventura" in raw:
            name = "Ventura"
        elif "sonoma" in raw:
            name = "Sonoma"
        elif "sequoia" in raw:
            name = "Sequoia"
        elif "tahoe" in raw:
            name= "Tahoe"
        else:
            continue  # skip unsupported installers

        spec = InstallerSpec(
            name,
            inst.version,
            inst.path,
            inst.size_bytes,
            f"{inst.size_gb} GB"
        )

        results.append(spec)

    return results


# ---------------------------------------------------------
# Validation helpers (unchanged)
# ---------------------------------------------------------

def validate_installer_structure(installer):
    """
    Ensures the installer has the required SharedSupport files.
    """
    path = installer["path"]
    shared = os.path.join(path, "Contents", "SharedSupport")

    required = [
        "InstallESD.dmg",
        "BaseSystem.dmg",
        "InstallInfo.plist",
    ]

    for filename in required:
        full = os.path.join(shared, filename)
        if not os.path.exists(full):
            return f"{installer['name']} is missing {filename}"

    return None


def validate_drive_capacity(installer, drive):
    installer_size = installer["size_bytes"]
    drive_size = drive.get("size_bytes", 0)

    if drive_size < installer_size:
        return f"{installer['name']} requires {installer['size_label']} but the drive is too small"

    return None


def validate_installers(selected_installers, selected_drive):
    """
    Ensures selected installers are supported and the drive is valid.
    """
    errors = []

    if not selected_installers:
        errors.append("No installers selected.")
        return errors

    if not selected_drive:
        errors.append("No target drive selected.")
        return errors

    VALID_NAMES = {
        "Sierra",
        "High Sierra",
        "Mojave",
        "Catalina",
        "Big Sur",
        "Monterey",
        "Ventura",
        "Sonoma",
    }

    for inst in selected_installers:
        name = inst.get("name", "")
        path = inst.get("path")

        if not path:
            errors.append(f"{name}: Installer path is missing.")
            continue

        if name not in VALID_NAMES:
            errors.append(f"{name}: Unsupported macOS version.")

    return errors
