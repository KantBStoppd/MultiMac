import os
import subprocess
import traceback
import datetime
import time
from dataclasses import dataclass
from typing import List, Callable, Optional
from .installer_scanner import find_installers_in_applications


LOG_PATH = os.path.expanduser("~/MultiMacOSInstaller.log")


def write_log(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


@dataclass
class BuildResult:
    success: bool
    error: Optional[str] = None


class BuildEngine:
    """
    MultiMac Build Engine (Single-Process, No Daemon)
    ------------------------------------------------
    Assumes the entire app is already running as root (sudo or AppleScript).
    """

    def __init__(
        self,
        installers: Optional[List] = None,
        drive: Optional[dict] = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self.installers = installers or []
        self.device = drive.get("device") if drive else None

        self.on_progress = on_progress or (lambda msg, pct: None)
        self.on_complete = on_complete or (lambda: None)
        self.on_error = on_error or (lambda msg: None)
        self.on_log = on_log or (lambda msg: None)
        self.on_installer_done = lambda name: None

    def get_installers(self):
        return find_installers_in_applications()

    def write_log(self, msg: str):
        write_log(msg)

    # ---------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------
    def run(self) -> BuildResult:
        # --- REQUIRED ROOT CHECK ---
        euid = os.geteuid()
        write_log(f"[DEBUG] Effective UID: {euid}")
        if euid != 0:
            raise RuntimeError(
                "MultiMac is not running as root. "
                "The launcher must execute the binary directly with sudo."
            )
        # ---------------------------
        write_log("=== MultiMac Build Started ===")
        write_log(f"Installers: {[i.name for i in self.installers]}")

        try:
            # Preflight: ensure installers selected
            if not self.installers:
                raise Exception("No installers selected")

            # Preflight: ensure disk is large enough (dynamic sizing)
            self._check_disk_size()

            self._progress("Preparing target disk…", 2)

            # 1. Erase disk → GPT + HFS+
            self._progress("Erasing disk and creating base layout…", 5)
            self._erase_disk()

            # 2. Create partitions
            self._progress("Creating installer partitions…", 15)
            self._create_partitions()

            # 3. Run CIM on each partition
            total = len(self.installers)
            for index, installer in enumerate(self.installers, start=1):
                pct = 15 + int((index / total) * 80)
                self._progress(f"Building {installer.name} installer…", pct)
                self._run_cim(installer)

            self._progress("Finalizing build…", 95)

            self._progress("Build complete.", 100)
            write_log("=== MultiMac Build Complete ===")
            self.on_complete()
            return BuildResult(success=True)

        except Exception as e:
            write_log("ENGINE ERROR: " + str(e))
            write_log(traceback.format_exc())
            msg = str(e)
            self.on_error(msg)
            return BuildResult(success=False, error=msg)


    # ---------------------------------------------------------
    # Preflight checks
    # ---------------------------------------------------------
    def _partition_size_for(self, name: str) -> int:
        """Return required partition size in bytes."""
        table = {
            "Sierra": 16,
            "High Sierra": 16,
            "Mojave": 20,
            "Catalina": 20,
            "Big Sur": 25,
            "Monterey": 25,
            "Ventura": 30,
            "Sonoma": 30,
            "Sequoia": 30,
            "Tahoe": 30,
        }
        return table.get(name, 16)

    def _check_disk_size(self):
        info = subprocess.check_output(["diskutil", "info", self.device], text=True)
        size_bytes = None

        for line in info.splitlines():
            if "Disk Size" in line and "Bytes" in line:
                part = line.split("(")[1].split(" ")[0]
                size_bytes = int(part)
                break

        if size_bytes is None:
            raise RuntimeError("Could not determine disk size.")

        required = sum(self._partition_size_for(i.name) for i in self.installers)

        if size_bytes < required:
            raise RuntimeError(
                f"Target disk too small. Requires at least {required / (1024**3):.0f} GB."
            )

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------
    def _progress(self, message: str, percent: int):
        try:
            if percent is None:
                return

            if not hasattr(self, "_last_percent"):
                self._last_percent = 0

            if percent < self._last_percent:
                return

            self._last_percent = percent
            self.on_progress(message, percent)
        except Exception:
            pass

    def _run(self, cmd: List[str]) -> str:
        self.on_log("[CMD] " + " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        output_lines = []
        for line in proc.stdout:
            if line.strip():
                line_stripped = line.strip()
                output_lines.append(line_stripped)
                self.on_log(line_stripped)
                write_log(line_stripped)
        proc.wait()
        output = "\n".join(output_lines)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\nExit code: {proc.returncode}\nOutput:\n{output}"
            )
        return output


    # ---------------------------------------------------------
    # Step 1: Erase disk
    # ---------------------------------------------------------
    def _erase_disk(self):
        out = self._run([
            "diskutil", "eraseDisk", "JHFS+", "MultiMac", "GPT", self.device
        ])
        if out.strip():
            write_log(out)


    # ---------------------------------------------------------
    # Step 2: Create partitions (GPT + eraseVolume)
    # ---------------------------------------------------------
    def _create_partitions(self):
        """
        Create HFS+ partitions using safe GPT workflow.
        Assumes process is already running as root.
        """
        # 0. Normalize device path
        if not self.device.startswith("/dev/"):
            self.device = f"/dev/{self.device}"

        # 1. Remove default HFS+ partition (disk2s2 from eraseDisk)
        self._run(["diskutil", "eraseVolume", "Free", "unused", f"{self.device}s2"])

        # 2. Partition disk using Apple's partitioner (replaces all GPT logic)
        args = ["diskutil", "partitionDisk", self.device, "GPT"]
        for installer in self.installers:
            size_gb = self._partition_size_for(installer.name)
            args += ["JHFS+", installer.name, f"{size_gb}g"]
        self._run(args)

        # 3. Format slices (macOS will auto‑mount them)
        for index, installer in enumerate(self.installers, start=2):
            slice_id = f"{self.device}s{index}"
            self._run([
                "diskutil", "eraseVolume", "HFS+", installer.name, slice_id
            ])

    # ---------------------------------------------------------
    # Step 3: Run CIM
    # ---------------------------------------------------------
    def _run_cim(self, installer):
        cim_path = os.path.join(
            installer.path,
            "Contents", "Resources", "createinstallmedia"
        )

        safe_name = installer.name
        volume_path = f"/Volumes/{safe_name}"

        self._progress(f"Preparing {installer.name} installer…", 0)
        self.on_log("Preparing createinstallmedia…")
        self._progress("Copying files…", 0)

        if installer.name == "Sierra":
            cmd = [
                cim_path,
                "--volume", volume_path,
                "--applicationpath", installer.path,
                "--nointeraction",
            ]
        else:
            cmd = [
                cim_path,
                "--volume", volume_path,
                "--nointeraction",
            ]

        out = self._run(cmd)
        if out.strip():
            self.on_log(out)

        self.on_installer_done(installer.name)

        self._progress("Finalizing installer…", 0)

        


    def convert_installer_to_iso(self, installer_path: str, output_dir: str) -> str:
        # --- BASIC NAMES ---
        name = os.path.basename(installer_path).replace(".app", "")
        safe = name.replace(" ", "_")

        temp_sparse = f"/tmp/{safe}.sparseimage"
        iso_cdr = os.path.join(output_dir, f"{safe}.iso.cdr")
        iso_final = os.path.join(output_dir, f"{safe}.iso")

        createinstallmedia = os.path.join(
            installer_path,
            "Contents",
            "Resources",
            "createinstallmedia",
        )

        # --- MOUNTPOINTS (osxiso style) ---
        build_mount = "/Volumes/install_build"
        base_mount = "/Volumes/OS X Base System"
        app_mount = "/Volumes/install_app"
        install_mount = f"/Volumes/Install {name}"

        # --- UNIVERSAL DETACH (osxiso logic) ---
        def detach_all():
            for mp in [install_mount, app_mount, base_mount, build_mount]:
                if os.path.isdir(mp):
                    try:
                        self._run(["hdiutil", "detach", "-force", mp])
                    except Exception:
                        pass

        # --- PREP CLEANUP ---
        detach_all()
        if os.path.exists(temp_sparse):
            try:
                os.remove(temp_sparse)
            except Exception:
                pass

        # --- KILL AUTO-MOUNT PROCESSES (osxiso-inspired) ---
        for proc in ["Finder", "DiskImageMounter", "mds", "mdworker", "asr"]:
            try:
                self._run(["killall", proc])
            except Exception:
                pass

        # --- CREATE SPARSEIMAGE ---
        self._run([
            "hdiutil", "create",
            "-o", temp_sparse,
            "-size", "16g",
            "-layout", "SPUD",
            "-fs", "HFS+J",
        ])

        # --- MOUNT SPARSEIMAGE ---
        self._run([
            "hdiutil", "attach",
            temp_sparse,
            "-noverify",
            "-nobrowse",
            "-mountpoint", build_mount,
        ])

        # --- SIERRA SPECIAL CASE ---
        is_sierra = ("Sierra" in name) or ("10.12" in name)

        if is_sierra:
            self._run([
                createinstallmedia,
                "--volume", build_mount,
                "--applicationpath", installer_path,
                "--nointeraction",
            ])
        else:
            self._run([
                createinstallmedia,
                "--volume", build_mount,
                "--nointeraction",
            ])

        # --- DETACH EVERYTHING (osxiso logic) ---
        detach_all()

        # --- FINAL DOUBLE-PASS DETACH (Mojave fix) ---
        for _ in range(2):
            info = self._run(["hdiutil", "info"])
            for line in info.splitlines():
                if build_mount in line or name in line:
                    disk = line.split()[0]  # /dev/diskX
                    try:
                        self._run(["hdiutil", "detach", "-force", disk])
                    except Exception:
                        pass

        # --- CONVERT TO ISO ---
        self._run([
            "hdiutil", "convert",
            temp_sparse,
            "-format", "UDZO",
            "-o", iso_cdr,
            "-quiet",
        ])

        # --- NORMALIZE OUTPUT (osxiso style) ---
        base = iso_cdr[:-4]  # strip .cdr
        candidates = [
            iso_cdr,
            base,
            base + ".iso",
            base + ".dmg",
            base + ".cdr.dmg",
        ]

        actual = None
        for c in candidates:
            if os.path.exists(c):
                actual = c
                break

        if actual is None:
            raise RuntimeError("ISO conversion failed: no output file produced")

        # --- FINAL RENAME ---
        final_iso = base if base.endswith(".iso") else base + ".iso"
        self._run(["mv", actual, final_iso])

        print(f"[ISO] Done: {final_iso}")
        sys.stdout.flush()

        # --- RETURN TO MULTIMAC MAIN MENU ---
        self.show_main_menu()

        return final_iso











