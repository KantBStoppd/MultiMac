import wx
import threading
import time
import wx.adv
import os
from ui.ui_widgets import (
    InstallerTile,
    USBPickerPanel,
    PartitionPreview,
    VersionTile,
    load_icon,
    ExpandableItem,
)

from theme import apply_dark
import wx.lib.newevent

InstallerSelectedEvent, EVT_INSTALLER_SELECTED = wx.lib.newevent.NewEvent()

from logic_installer import InstallerSpec
from logic_installer import detect_installers
from logic_drive import detect_drives
from engine.build_engine import BuildEngine
from engine.utils import resource_path
from ui.ui_widgets import GradientButton

VERSION_COLORS = {
    "Sierra": wx.Colour(100, 140, 100),
    "High Sierra": wx.Colour(80, 120, 80),
    "Mojave": wx.Colour(111, 78, 55),
    "Catalina": wx.Colour(180, 60, 60),
    "Big Sur": wx.Colour(52, 120, 246),
    "Monterey": wx.Colour(155, 81, 224),
    "Ventura": wx.Colour(255, 140, 0),
    "Sonoma": wx.Colour(0, 150, 100),
    "Sequoia": wx.Colour(0, 110, 160),
    "Tahoe": wx.Colour(52, 120, 180),
}
# =========================================================
# Welcome Panel
# =========================================================
class WelcomePanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        apply_dark(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add((20, 40))

        rel_path = "assets/multimac.png"
        full_path = resource_path(rel_path)

        print(f"[ui_panels] Loading image: {full_path}")
        print(f"[ui_panels] Exists: {os.path.exists(full_path)}")

        if os.path.exists(full_path):
            try:
                img = wx.Image(full_path, wx.BITMAP_TYPE_PNG)
            except Exception as e:
                print(f"[ui_panels] wx.Image failed: {e}")
                img = None
        else:
            print(f"[ui_panels] MISSING FILE: {full_path}")
            img = None

        target_width = 500
        scale = target_width / img.GetWidth()
        img = img.Scale(int(img.GetWidth() * scale), int(img.GetHeight() * scale))
        bmp = wx.Bitmap(img)

        self.logo = wx.StaticBitmap(self, -1, bmp)
        main_sizer.Add(self.logo, 0, wx.ALIGN_CENTER_HORIZONTAL)

        title = wx.StaticText(self, -1, "Multi‑macOS Installation Maker")
        title.SetFont(wx.Font(20, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 10)

        desc = wx.StaticText(
            self,
            -1,
            "This software will help you create a macOS installation USB with multiple versions of macOS on the same drive."
        )
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(desc, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.btn_begin = GradientButton(self, label="Begin")
        main_sizer.Add(self.btn_begin, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        self.btn_download = GradientButton(self, label="Download macOS Installers")
        main_sizer.Add(self.btn_download, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        self.btn_iso = GradientButton(self, label="Convert macOS Installer to ISO")
        main_sizer.Add(self.btn_iso, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        self.SetSizer(main_sizer)
# =========================================================
# Drive Selection Panel
# =========================================================
class DrivePanel(wx.Panel):
    def __init__(self, parent, on_back=None, on_next=None):
        super().__init__(parent)
        apply_dark(self)

        self.on_back = on_back
        self.on_next = on_next
        self.selected_drive = None

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Select Target USB Drive")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title, 0, wx.LEFT | wx.TOP | wx.RIGHT, 20)

        self.usb_picker = USBPickerPanel(self, on_select=self._on_drive_selected)
        main_sizer.Add(self.usb_picker, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = GradientButton(self, label="Back")
        self.btn_next = GradientButton(self, label="Next")
        self.btn_next.Disable()

        btn_sizer.Add(self.btn_back, 0, wx.ALL, 10)
        btn_sizer.Add(self.btn_next, 0, wx.ALL, 10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT)

        self.SetSizer(main_sizer)

        self.btn_back.Bind(wx.EVT_BUTTON, self._on_back)
        self.btn_next.Bind(wx.EVT_BUTTON, self._on_next)

    def RefreshDrives(self):
        drives = detect_drives()
        self.usb_picker.LoadDrives(drives)
        self.btn_next.Disable()
        self.selected_drive = None

    def _on_drive_selected(self, drive_dict):
        self.selected_drive = drive_dict
        self.btn_next.Enable()

    def _on_back(self, event):
        if self.on_back:
            self.on_back()

    def _on_next(self, event=None):
        if not self.selected_drive:
            wx.MessageBox("Please select a USB drive.", "No Drive Selected")
            return
        self.on_next(self.selected_drive)

# =========================================================
# Installers Panel (UI1, fixed tiles, Tahoe removed)
# =========================================================
class InstallersPanel(wx.Panel):
    def __init__(self, parent, on_back=None, on_next=None):
        super().__init__(parent)
        apply_dark(self)

        self.on_back = on_back
        self.on_next = on_next

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Select macOS Installers")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title, 0, wx.LEFT | wx.TOP | wx.RIGHT, 20)

        # Fixed tile list (oldest → newest)
        versions = [
            "Sierra",
            "High Sierra",
            "Mojave",
            "Catalina",
            "Big Sur",
            "Monterey",
            "Ventura",
            "Sonoma",
            "Sequoia",
            "Tahoe",
        ]

        self.tiles = {}
        grid = wx.GridSizer(rows=0, cols=3, hgap=10, vgap=10)

        for version in versions:
            tile = VersionTile(self, version)
            self.tiles[version] = tile
            grid.Add(tile, 0, wx.EXPAND)

        main_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = GradientButton(self, label="Back")
        self.btn_next = GradientButton(self, label="Next")
        self.Bind(EVT_INSTALLER_SELECTED, self._on_installer_selected)

        nav.Add(self.btn_back, 0, wx.ALL, 10)
        nav.Add(self.btn_next, 0, wx.ALL, 10)
        main_sizer.Add(nav, 0, wx.ALIGN_LEFT)

        self.SetSizer(main_sizer)

        self.btn_back.Bind(wx.EVT_BUTTON, self._on_back)
        self.btn_next.Bind(wx.EVT_BUTTON, self._on_next)

    def RefreshInstallers(self):
        installers = detect_installers()

        for tile in self.tiles.values():
            tile.SetStatus(False)

        for inst in installers:
            name = inst.name.strip()
            lower = name.lower()

            for key, tile in self.tiles.items():
                if key.lower() == lower:
                    tile.SetStatus(True, inst.path)
                    tile.size_bytes = inst.size_bytes
                    break

        self.Layout()

    def _on_back(self, event):
        if self.on_back:
            self.on_back()

    def _on_next(self, event=None):
        selected_installers = []

        for tile in self.tiles.values():
            if tile.selected and tile.installer_path and tile.size_bytes:
                icon_name = tile.name.replace(" ", "").lower()

                spec = InstallerSpec(
                    tile.name,          # name
                    "",                 # version (unused)
                    tile.installer_path,
                    tile.size_bytes,
                    f"{round(tile.size_bytes / (1024**3), 1)} GB"
                )

                spec.icon = f"assets/icons/{icon_name}.png"
                selected_installers.append(spec)

        if not selected_installers:
            wx.MessageBox("No installers selected.", "Error")
            return

        self.on_next(selected_installers)

    def _on_installer_selected(self, event):
        for tile in self.tiles.values():
            tile.selected = (tile.installer_path == event.path)
        self.Layout()
# =========================================================
# Overview Panel
# =========================================================
class OverviewPanel(wx.Panel):
    def __init__(self, parent, on_back=None, on_start=None):
        super().__init__(parent)
        apply_dark(self)

        self.on_back = on_back
        self.on_start = on_start
        self.selected_installers = []
        self.selected_drive = None

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Overview")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title, 0, wx.ALL, 10)

        self.lbl_drive = wx.StaticText(self, label="")
        main_sizer.Add(self.lbl_drive, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.summary_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.summary_sizer, 0, wx.ALL, 10)

        self.preview = PartitionPreview(self)
        self.preview.SetMinSize((300, 80))
        main_sizer.Add(self.preview, 0, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = GradientButton(self, label="Back")
        self.btn_start = GradientButton(self, label="Start")
        btn_sizer.Add(self.btn_back, 0, wx.ALL, 10)
        btn_sizer.Add(self.btn_start, 0, wx.ALL, 10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT)

        self.SetSizer(main_sizer)

        self.btn_back.Bind(wx.EVT_BUTTON, self._on_back)
        self.btn_start.Bind(wx.EVT_BUTTON, self._on_start)

    def _load_icon(self, name):
        bmp = load_icon(name)

        if bmp is None:
            print(f"[VersionTile] Icon missing for '{name}'")
            return None

        try:
            img = bmp.ConvertToImage().Scale(24, 24, wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(img)
        except Exception as e:
            print(f"[VersionTile] Failed to scale icon '{name}': {e}")
            return None

    def _load_icon_path(self, icon_path):
        if not icon_path:
            return None

        full = resource_path(icon_path)

        if not os.path.exists(full):
            print("[OverviewPanel] Missing icon:", full)
            return None

        try:
            bmp = wx.Bitmap(full)
            img = bmp.ConvertToImage().Scale(24, 24, wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(img)
        except Exception as e:
            print("[OverviewPanel] Failed to load icon:", full, e)
            return None

    def RefreshSummary(self):
        if self.selected_drive:
            name = self.selected_drive.get("name", "Unknown Drive")
            size = self.selected_drive.get("size", 0)
            size_gb = round(size / (1024**3), 1)
            self.lbl_drive.SetLabel(f"Target Drive: {name} — {size_gb} GB")
        else:
            self.lbl_drive.SetLabel("No drive selected.")

        self.summary_sizer.Clear(True)

        if not self.selected_installers:
            self.summary_sizer.Add(wx.StaticText(self, label="No installers selected."), 0, wx.BOTTOM, 5)
            self.preview.SetSegments([])
            self.Layout()
            return

        segments = []
        total_size = 0

        for inst in self.selected_installers:
            name = inst.name
            size = inst.size_bytes or 0
            size_gb = round(size / (1024**3), 1)
            total_size += size

            row = wx.BoxSizer(wx.HORIZONTAL)
            icon = self._load_icon_path(inst.icon)
            if icon:
                row.Add(wx.StaticBitmap(self, -1, icon), 0, wx.RIGHT, 6)

            row.Add(wx.StaticText(self, label=f"{name} — {size_gb} GB"), 0)
            self.summary_sizer.Add(row, 0, wx.BOTTOM, 4)

            color = VERSION_COLORS.get(name, wx.Colour(70, 130, 180))
            segments.append({"label": name, "size": size, "color": color})

        total_gb = round(total_size / (1024**3), 1)
        self.summary_sizer.Add(wx.StaticText(self, label=f"Total Size: {total_gb} GB"), 0, wx.TOP, 6)

        self.preview.SetSegments(segments)
        self.Layout()

    def _on_back(self, event):
        if self.on_back:
            self.on_back()

    def _on_start(self, event):
        self.on_start(self.selected_installers, self.selected_drive)
# =========================================================
# Progress Panel
# =========================================================
class ProgressPanel(wx.Panel):
    def __init__(self, parent, installers, drive, on_complete, on_error, on_cancel):
        super().__init__(parent)
        apply_dark(self)

        self._alive = True
        self.installers = installers
        self.drive = drive

        self.on_complete = on_complete
        self.on_error = on_error
        self.on_cancel = on_cancel

        self.stop_event = threading.Event()
        self._smooth_progress = 0
        self._target_progress = 0
        self.start_time = time.time()

        # Build UI
        self._build_ui()

        # ---------------------------------------------------------
        # ENGINE (ALL CALLBACKS WRAPPED IN wx.CallAfter)
        # ---------------------------------------------------------
        self.engine = BuildEngine(
            installers=installers,
            drive=drive,
            on_progress=lambda msg, pct: wx.CallAfter(self._on_engine_progress, msg, pct),
            on_complete=lambda: wx.CallAfter(self._on_engine_complete),
            on_error=lambda msg: wx.CallAfter(self._on_engine_error, msg),
            on_log=lambda msg: wx.CallAfter(self.log, msg),
        )

        # Installer‑done callback (checkmark)
        self.engine.on_installer_done = lambda name: wx.CallAfter(self.mark_installer_done, name)

        # Run engine in background thread
        threading.Thread(target=self.engine.run, daemon=True).start()

        wx.CallLater(50, self._smooth_progress_tick)
        wx.CallLater(1000, self._update_eta)

    # ---------------------------------------------------------
    # CHECKMARK UPDATE
    # ---------------------------------------------------------
    def mark_installer_done(self, name):
        check = self.check_items.get(name)
        if check:
            check.SetLabel("[✔]")
            check.Refresh()

    # ---------------------------------------------------------
    # UI BUILD
    # ---------------------------------------------------------
    def _build_ui(self):
        main = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Building Multi‑Installer USB…")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main.Add(title, 0, wx.LEFT | wx.TOP | wx.RIGHT, 20)

        divider = wx.StaticLine(self)
        main.Add(divider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Spinner + status
        status_row = wx.BoxSizer(wx.HORIZONTAL)

        self.spinner = wx.ActivityIndicator(self)
        self.spinner.Start()
        status_row.Add(self.spinner, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)

        self.status_label = wx.StaticText(self, label="Starting…")
        self.status_label.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        status_row.Add(self.status_label, 1, wx.ALIGN_CENTER_VERTICAL)

        main.Add(status_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ETA
        self.eta_label = wx.StaticText(self, label="Elapsed: 0s")
        self.eta_label.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main.Add(self.eta_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Progress bar
        self.progress = wx.Gauge(self, range=100, size=(400, 25))
        main.Add(self.progress, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Installers checklist
        checklist_box = wx.StaticBox(self, label="Installers")
        checklist_sizer = wx.StaticBoxSizer(checklist_box, wx.VERTICAL)

        self.check_items = {}
        for inst in self.installers:
            row = wx.BoxSizer(wx.HORIZONTAL)
            check = wx.StaticText(self, label="[ ]")
            label = wx.StaticText(self, label=inst.name)
            row.Add(check, 0, wx.RIGHT, 8)
            row.Add(label)
            checklist_sizer.Add(row, 0, wx.TOP | wx.BOTTOM, 4)
            self.check_items[inst.name] = check

        main.Add(checklist_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # Log window
        self.log_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(500, 250)
        )
        main.Add(self.log_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        # Cancel button
        self.btn_cancel = GradientButton(self, label="Cancel")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self._on_cancel)
        main.Add(self.btn_cancel, 0, wx.ALL, 10)

        self.SetSizer(main)

    # ---------------------------------------------------------
    # ENGINE CALLBACKS (MAIN THREAD ONLY)
    # ---------------------------------------------------------
    def _on_cancel(self, event):
        if self.on_cancel:
            self.on_cancel()

    def _on_engine_progress(self, message, percent):
        self.update_status(message)
        self.update_progress(percent)

    def _on_engine_complete(self):
        if hasattr(self, "spinner"):
            self.spinner.Stop()

        self._target_progress = 100
        self._smooth_progress = 100
        self.progress.SetValue(100)

        self.update_status("Finishing…")

        if self.on_complete:
            wx.CallLater(350, self.on_complete)

    def _on_engine_error(self, message):
        if hasattr(self, "spinner"):
            self.spinner.Stop()

        self.log(f"[ERROR] {message}")

        if self.on_error:
            wx.CallAfter(self.on_error, message)

    # ---------------------------------------------------------
    # UI HELPERS
    # ---------------------------------------------------------
    def update_status(self, text):
        if not self._alive:
            return
        try:
            self.status_label.SetLabel(text)
        except RuntimeError:
            pass

    def update_progress(self, value):
        self._target_progress = max(0, min(100, value))

    def _smooth_progress_tick(self):
        if self.stop_event.is_set():
            return

        diff = self._target_progress - self._smooth_progress
        self._smooth_progress += diff * 0.10
        self.progress.SetValue(int(self._smooth_progress))

        wx.CallLater(50, self._smooth_progress_tick)

    def _update_eta(self):
        if self.stop_event.is_set():
            return
        elapsed = int(time.time() - self.start_time)
        self.eta_label.SetLabel(f"Elapsed: {elapsed}s")
        wx.CallLater(1000, self._update_eta)

    # ---------------------------------------------------------
    # LOGGING
    # ---------------------------------------------------------
    def log(self, message):
        wx.CallAfter(self._append_log, message)

    def _append_log(self, message):
        try:
            self.log_ctrl.AppendText(message + "\n")
        except Exception:
            pass
            
class SuccessPanel(wx.Panel):
    def __init__(self, parent, installers, drive_name, on_finish):
        super().__init__(parent)
        apply_dark(self)

        self.on_finish = on_finish

        main = wx.BoxSizer(wx.VERTICAL)

        # --- Big Green Checkmark ---
        check_path = resource_path("assets/icons/check.png")
        if os.path.exists(check_path):
            check_bmp = wx.Bitmap(check_path, wx.BITMAP_TYPE_PNG)
            check_img = wx.StaticBitmap(self, bitmap=check_bmp)
            main.Add(check_img, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 20)
        else:
            fallback = wx.StaticText(self, label="✔")
            fallback.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            fallback.SetForegroundColour(wx.Colour(0, 200, 0))
            main.Add(fallback, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 20)

        title = wx.StaticText(self, label="Build Complete!")
        title.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main.Add(title, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        msg = wx.StaticText(
            self,
            label=f"Your Multi‑macOS USB installer has been successfully created on {drive_name}."
        )
        msg.SetFont(wx.Font(13, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main.Add(msg, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        list_box = wx.StaticBox(self, label="Included Installers")
        list_sizer = wx.StaticBoxSizer(list_box, wx.VERTICAL)

        for inst in installers:
            list_sizer.Add(wx.StaticText(self, label=f"• {inst.name}"), 0, wx.TOP | wx.BOTTOM, 3)

        main.Add(list_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        btn = GradientButton(self, label="Finish")
        btn.Bind(wx.EVT_BUTTON, lambda evt: self.on_finish())
        main.Add(btn, 0, wx.ALIGN_CENTER | wx.ALL, 20)

        self.SetSizer(main)


class ErrorPanel(wx.Panel):
    def __init__(self, parent, error_message, on_back, on_troubleshoot):
        super().__init__(parent)
        apply_dark(self)

        self.on_back = on_back
        self.on_troubleshoot = on_troubleshoot

        main = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="An Error Occurred")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main.Add(title, 0, wx.ALL, 20)

        msg = wx.StaticText(self, label=error_message)
        msg.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        btn_back = GradientButton(self, label="Back")
        btn_back.Bind(wx.EVT_BUTTON, lambda evt: self.on_back())
        btn_sizer.Add(btn_back, 0, wx.ALL, 10)

        btn_trouble = GradientButton(self, label="Troubleshooting")
        btn_trouble.Bind(wx.EVT_BUTTON, lambda evt: self.on_troubleshoot())
        btn_sizer.Add(btn_trouble, 0, wx.ALL, 10)

        main.Add(btn_sizer, 0, wx.ALIGN_LEFT)

        self.SetSizer(main)


class TroubleshootingPanel(wx.Panel):
    def __init__(self, parent, on_back):
        super().__init__(parent)
        apply_dark(self)
        self.on_back = on_back

        main = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Troubleshooting")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main.Add(title, 0, wx.LEFT | wx.TOP | wx.RIGHT, 20)

        divider = wx.StaticLine(self)
        main.Add(divider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        item = ExpandableItem(
            self,
            title="Sierra installer fails with 'not a valid mount point'",
            body=(
                "Run this command:\n\n"
                "sudo plutil -replace CFBundleShortVersionString -string \"12.6.03\" "
                "/Applications/Install\\ macOS\\ Sierra.app/Contents/Info.plist"
            )
        )
        main.Add(item, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        back_btn = GradientButton(self, label="Back")
        back_btn.Bind(wx.EVT_BUTTON, self._handle_back)
        main.Add(back_btn, 0, wx.ALL, 15)

        self.SetSizer(main)

    def _handle_back(self, event):
        self.on_back()


class ConvertISOPanel(wx.Panel):
    def __init__(self, parent, mainframe):
        super().__init__(parent)
        self.mainframe = mainframe
        self.engine = mainframe.engine
        self.installers = []
        self.build_ui()
        self.refresh_installers()

    def build_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Convert macOS Installer to ISO")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(title, 0, wx.ALL, 10)

        vbox.Add(wx.StaticText(self, label="Select macOS Installer:"), 0, wx.LEFT | wx.TOP, 10)
        self.dropdown = wx.ComboBox(self, style=wx.CB_READONLY)
        vbox.Add(self.dropdown, 0, wx.EXPAND | wx.ALL, 10)

        vbox.Add(wx.StaticText(self, label="Output Folder:"), 0, wx.LEFT, 10)
        self.output_picker = wx.DirPickerCtrl(self, message="Choose output folder")
        vbox.Add(self.output_picker, 0, wx.EXPAND | wx.ALL, 10)

        self.convert_btn = wx.Button(self, label="Convert to ISO")
        self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
        vbox.Add(self.convert_btn, 0, wx.ALL, 10)

        self.log_box = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        vbox.Add(self.log_box, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(vbox)

    def refresh_installers(self):
        self.installers = self.engine.get_installers()
        names = [i.name for i in self.installers]
        self.dropdown.Set(names)

    def log(self, msg):
        self.log_box.AppendText(msg + "\n")
        self.engine.write_log("[ISO] " + msg)

    def on_convert(self, event):
        idx = self.dropdown.GetSelection()
        if idx == wx.NOT_FOUND:
            self.log("No installer selected.")
            return

        installer = self.installers[idx]
        installer_path = installer.path
        output_dir = self.output_picker.GetPath()

        if not output_dir:
            self.log("No output folder selected.")
            return

        self.log(f"Starting ISO conversion for {installer.name}...")
        self.convert_btn.Disable()

        def run():
            try:
                iso_path = self.engine.convert_installer_to_iso(installer_path, output_dir)
                wx.CallAfter(self.log, f"ISO created: {iso_path}")
            except Exception as e:
                wx.CallAfter(self.log, f"Error: {e}")
            finally:
                wx.CallAfter(self.convert_btn.Enable)

        threading.Thread(target=run).start()