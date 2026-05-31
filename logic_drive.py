import subprocess
import plistlib


def detect_drives():
    try:
        result = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True,
            text=False,
            check=True
        )
        plist = plistlib.loads(result.stdout)
    except Exception as e:
        print("detect_drives() failed:", e)
        return []

    drives = []

    for item in plist.get("AllDisksAndPartitions", []):
        device_id = item.get("DeviceIdentifier")
        if not device_id:
            continue

        device = f"/dev/{device_id}"

        # We will store the FIRST mounted partition under /Volumes
        mount_point = None

        for part in item.get("Partitions", []):
            mount = part.get("MountPoint", "")
            if mount.startswith("/Volumes/"):
                mount_point = mount
                break

        if not mount_point:
            continue

        size = item.get("Size", 0)
        name = item.get("VolumeName") or device_id

        if size > 0:
            drives.append({
                "device": device,
                "name": name,
                "size_bytes": size,
                "type": "USB",
                "mount_point": mount_point,   # ← THIS IS THE CORRECT ONE
            })

    return drives

