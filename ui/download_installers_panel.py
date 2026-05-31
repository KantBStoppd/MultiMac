import wx
import threading
import os

from engine.installer_catalog import INSTALLER_CATALOG
from engine.downloader import download_installer
from engine.utils import resource_path
from theme import apply_dark, DARK_BG, DARK_PANEL, DARK_TEXT, DARK_SUBTEXT



class DownloadInstallersPanel(wx.Panel):
    def __init__(self, parent, on_back, on_refresh_installers):
        super().__init__(parent)
        self.on_back = on_back
        self.on_refresh_installers = on_refresh_installers

        self.rows = {}  # identifier → row widgets

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Download macOS Installers")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title, 0, wx.ALL, 10)

        # Refresh button
        refresh_btn = wx.Button(self, label="Refresh Installer List")
        refresh_btn.Bind(wx.EVT_BUTTON, lambda evt: self.load_installers())
        main_sizer.Add(refresh_btn, 0, wx.ALL, 10)

        # Scroll area
        self.scroller = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self.scroller.SetScrollRate(5, 5)
        self.list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroller.SetSizer(self.list_sizer)
        main_sizer.Add(self.scroller, 1, wx.EXPAND | wx.ALL, 10)

        # Back button
        back_btn = wx.Button(self, label="Back")
        back_btn.Bind(wx.EVT_BUTTON, lambda evt: self.on_back())
        main_sizer.Add(back_btn, 0, wx.ALL, 10)

        self.SetSizer(main_sizer)

        # Load installers on startup
        self.load_installers()

        apply_dark(self)
        self.SetBackgroundColour(DARK_BG)


    # ---------------------------------------------------------
    # Load installer list
    # ---------------------------------------------------------
    def load_installers(self):
        self.list_sizer.Clear(True)
        self.rows.clear()

        try:
            installers = INSTALLER_CATALOG
            print("NEW PIPELINE INSTALLERS:", installers)
        except Exception as e:
            wx.MessageBox(f"Failed to load installers:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
            return

        for entry in installers:
            self._add_row(entry)

        self.Layout()
        self.scroller.Layout()

    # ---------------------------------------------------------
    # Add a row for each installer
    # ---------------------------------------------------------
    def _add_row(self, entry):
        identifier = entry["identifier"]

        row_panel = wx.Panel(self.scroller)
        apply_dark(row_panel)
        row_panel.SetBackgroundColour(DARK_PANEL)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        name = entry.get("name", "Unknown macOS")
        version = entry.get("version", "Unknown")
        build = entry.get("build", "Unknown")
        size = entry.get("size")

        size_str = f" ({round(size / (1024**3), 1)} GB)" if size else ""

        # ICON
        icon_path = entry.get("icon")
        bmp = None

        if icon_path:
            abs_path = resource_path(icon_path)
            if os.path.exists(abs_path):
                try:
                    bmp = wx.Bitmap(abs_path, wx.BITMAP_TYPE_PNG)
                except:
                    bmp = None

        if bmp:
            icon = wx.StaticBitmap(row_panel, -1, bmp, size=(48, 48))
            row_sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        else:
            row_sizer.Add((48, 48), 0, wx.ALL, 5)

        # LABEL
        label = wx.StaticText(
            row_panel,
            label=f"{name}  ({version})  Build {build}{size_str}"
        )
        label.SetForegroundColour(DARK_TEXT)
        row_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        # STATUS
        status = wx.StaticText(row_panel, label="Ready")
        status.SetForegroundColour(DARK_SUBTEXT)
        row_sizer.Add(status, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        # PROGRESS
        progress = wx.Gauge(row_panel, range=100, size=(120, 20))
        row_sizer.Add(progress, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        # BUTTON
        btn = wx.Button(row_panel, label="Download")
        btn.Bind(wx.EVT_BUTTON, lambda evt, e=entry: self._start_download_thread(e))
        row_sizer.Add(btn, 0, wx.ALL, 5)

        row_panel.SetSizer(row_sizer)
        self.list_sizer.Add(row_panel, 0, wx.EXPAND | wx.ALL, 5)

        self.rows[identifier] = {
            "entry": entry,
            "panel": row_panel,
            "status": status,
            "progress": progress,
            "button": btn,
        }

    # ---------------------------------------------------------
    # Download thread wrapper
    # ---------------------------------------------------------
    def _start_download_thread(self, entry):
        t = threading.Thread(target=self._download_worker, args=(entry,))
        t.daemon = True
        t.start()

    # ---------------------------------------------------------
    # Download worker
    # ---------------------------------------------------------
    def _download_worker(self, entry):
        identifier = entry["identifier"]
        row = self.rows.get(identifier)
        if not row:
            return

        row["status"].SetLabel("Downloading...")
        row["progress"].SetValue(5)

        try:
            dest_dir = os.path.expanduser("~/Downloads/macOSInstallers")
            os.makedirs(dest_dir, exist_ok=True)

            dest = os.path.join(dest_dir, f"{entry['name']}.pkg")

            download_installer(entry["url"], dest)

            wx.CallAfter(row["progress"].SetValue, 100)
            wx.CallAfter(row["status"].SetLabel, "Extracting...")

            # Extraction is handled by MainFrame
            wx.CallAfter(self.GetParent().GetParent().start_download, entry, self)

        except Exception as e:
            wx.CallAfter(row["status"].SetLabel, "Error")
            wx.CallAfter(wx.MessageBox, f"Download failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    # ---------------------------------------------------------
    # UI callbacks from MainFrame
    # ---------------------------------------------------------
    def update_progress(self, entry, percent):
        row = self.rows.get(entry["identifier"])
        if row:
            row["progress"].SetValue(percent)

    def download_complete(self, entry, app_path):
        row = self.rows.get(entry["identifier"])
        if row:
            row["status"].SetLabel("Complete")
            row["progress"].SetValue(100)

    def download_error(self, entry, message):
        row = self.rows.get(entry["identifier"])
        if row:
            row["status"].SetLabel("Error")
        wx.MessageBox(message, "Error", wx.OK | wx.ICON_ERROR)
