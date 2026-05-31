import wx
import os
from ui.ui_panels import (
    WelcomePanel,
    DrivePanel,
    InstallersPanel,
    OverviewPanel,
    ProgressPanel,
    SuccessPanel,
    ErrorPanel,
    TroubleshootingPanel,
    ConvertISOPanel,
)
from ui.download_installers_panel import DownloadInstallersPanel
from engine.build_engine import (
    write_log,
    BuildEngine,
)
from engine.utils import resource_path
from engine.downloader import download_installer
from engine.installer_extractor import InstallerExtractor


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        write_log("=== APP STARTED ====")
        super(MainFrame, self).__init__(*args, **kwargs)

        # Engines
        self.extractor = InstallerExtractor()
        self.engine = BuildEngine()

        self.SetSize((900, 600))
        self.SetTitle("Multi‑macOS Installation Maker")

        icon_path = resource_path("assets/icon.icns")
        try:
            icon = wx.Icon(icon_path, wx.BITMAP_TYPE_ICON)
            self.SetIcon(icon)
        except Exception:
            pass

        # Main container panel
        self.panel_content = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel_content.SetSizer(self.sizer)

        # State
        self.selected_drive = None
        self.selected_installers = []
        self.last_installers = []
        self.dynamic_panel = None

        # Static pages
        self.page_welcome = WelcomePanel(self.panel_content)

        self.page_convert_iso = ConvertISOPanel(
            parent=self.panel_content,
            mainframe=self
        )

        self.page_drive = DrivePanel(
            self.panel_content,
            on_back=self.ShowWelcome,
            on_next=self.ShowInstallersWithDrive,
        )

        self.page_installers = InstallersPanel(
            self.panel_content,
            on_back=self.ShowDrive,
            on_next=self.OnInstallersNext,
        )

        self.page_overview = OverviewPanel(
            self.panel_content,
            on_back=self.ShowInstallers,
            on_start=self.StartBuildProcess,
        )

        self.page_download = DownloadInstallersPanel(
            self.panel_content,
            on_back=lambda: self.show_page("welcome"),
            on_refresh_installers=self._refresh_installers,
        )

        self.page_troubleshooting = TroubleshootingPanel(
            self.panel_content,
            on_back=self.show_error_panel
        )

        self.page_error = ErrorPanel(
            self.panel_content,
            error_message="",
            on_back=self.ShowOverview,
            on_troubleshoot=self.show_troubleshooting_panel
        )
        self.page_troubleshooting.Hide()
        self.page_error.Hide()

        # Registry
        self.pages = {
            "welcome": self.page_welcome,
            "drive": self.page_drive,
            "installers": self.page_installers,
            "overview": self.page_overview,
            "download": self.page_download,
            "error": self.page_error,
            "troubleshooting": self.page_troubleshooting,
            "convert_iso": self.page_convert_iso,
        }

        # Welcome buttons
        self.page_welcome.btn_begin.Bind(
            wx.EVT_BUTTON, lambda evt: self.ShowDrive()
        )
        self.page_welcome.btn_download.Bind(
            wx.EVT_BUTTON, lambda evt: self.show_page("download")
        )
        self.page_welcome.btn_iso.Bind(
            wx.EVT_BUTTON, lambda evt: self.show_page("convert_iso")
        )

        # Start on welcome
        self._show_page(self.page_welcome)

        self.Layout()
        self.Show()

    # ---------------------------------------------------------
    # Core page switching
    # ---------------------------------------------------------
    def _clear_sizer(self):
        while self.sizer.GetItemCount():
            item = self.sizer.GetItem(0)
            window = item.GetWindow()
            if window:
                self.sizer.Detach(window)
            else:
                self.sizer.Remove(0)

    def _show_page(self, page):
        # Stop background loops on old dynamic panel
        try:
            if hasattr(self, "dynamic_panel") and hasattr(self.dynamic_panel, "stop_event"):
                self.dynamic_panel.stop_event.set()
        except:
            pass

        # Stop spinner on old dynamic panel if present
        try:
            if hasattr(self, "dynamic_panel") and hasattr(self.dynamic_panel, "spinner"):
                self.dynamic_panel.spinner.Stop()
        except:
            pass

        # Hide static pages
        for p in self.pages.values():
            p.Hide()

        # Destroy dynamic panel
        if self.dynamic_panel and self.dynamic_panel in self.panel_content.GetChildren():
            try:
                self.dynamic_panel.Hide()
                self.dynamic_panel.Destroy()
            except:
                pass
        self.dynamic_panel = None

        # Show requested page
        self._clear_sizer()
        if page.GetParent() is not self.panel_content:
            page.Reparent(self.panel_content)

        self.sizer.Add(page, 1, wx.EXPAND)
        page.Show()
        self.panel_content.Layout()

    def _switch_to_dynamic(self, panel):
        # Stop background loops on old dynamic panel
        try:
            if hasattr(self, "dynamic_panel") and hasattr(self.dynamic_panel, "stop_event"):
                self.dynamic_panel.stop_event.set()
        except:
            pass

        # Hide static pages
        for p in self.pages.values():
            p.Hide()

        self.panel_content.Freeze()

        # Destroy old dynamic panel
        if self.dynamic_panel and self.dynamic_panel is not panel:
            if self.dynamic_panel in self.panel_content.GetChildren():
                try:
                    if hasattr(self.dynamic_panel, "spinner"):
                        self.dynamic_panel.spinner.Stop()

                    self.dynamic_panel.Hide()
                    self.dynamic_panel.Destroy()
                except:
                    pass

        self.dynamic_panel = panel

        self._clear_sizer()
        if panel.GetParent() is not self.panel_content:
            panel.Reparent(self.panel_content)

        self.sizer.Add(panel, 1, wx.EXPAND)
        panel.Show()

        self.panel_content.Layout()
        self.panel_content.Thaw()

    def show_page(self, name):
        page = self.pages.get(name)
        if not page:
            print(f"Unknown page: {name}")
            return
        self._show_page(page)

    # ---------------------------------------------------------
    # Navigation helpers
    # ---------------------------------------------------------
    def ShowWelcome(self):
        self._show_page(self.page_welcome)

    def ShowDrive(self):
        self.page_drive.RefreshDrives()
        self._show_page(self.page_drive)

    def ShowInstallers(self):
        self.page_installers.RefreshInstallers()
        self._show_page(self.page_installers)

    def ShowInstallersWithDrive(self, drive):
        self.selected_drive = drive
        self.ShowInstallers()

    def ShowOverview(self):
        self.page_overview.selected_installers = self.selected_installers
        self.page_overview.selected_drive = self.selected_drive
        self.page_overview.RefreshSummary()
        self._show_page(self.page_overview)

    def show_troubleshooting_panel(self):
        self._show_page(self.page_troubleshooting)

    def show_error_panel(self):
        self._show_page(self.page_error)

    # ---------------------------------------------------------
    # Callbacks from panels
    # ---------------------------------------------------------
    def OnDriveSelected(self, device_id):
        self.selected_drive = device_id
        self.ShowInstallersWithDrive(device_id)

    def OnInstallersNext(self, selected_tiles):
        self.selected_installers = selected_tiles
        self.ShowOverview()

    def OnStartProcess(self):
        if self.selected_installers and self.selected_drive:
            self.StartBuildProcess(self.selected_installers, self.selected_drive)

    def StartBuildProcess(self, installers, drive):
        self.last_installers = installers
        self.selected_drive = drive
        self.ShowProgress(installers, drive)

    # ---------------------------------------------------------
    # Dynamic panels
    # ---------------------------------------------------------
    def ShowProgress(self, installers, drive):
        panel = ProgressPanel(
            parent=self.panel_content,
            installers=installers,
            drive=drive,
            on_complete=self.ShowComplete,
            on_error=self.ShowError,
            on_cancel=self.CancelBuild,
        )
        self._switch_to_dynamic(panel)

    def ShowComplete(self):
        drive_name = (
            self.selected_drive.get("name", "USB Drive")
            if isinstance(self.selected_drive, dict)
            else "USB Drive"
        )

        panel = SuccessPanel(
            parent=self.panel_content,
            installers=self.last_installers,
            drive_name=drive_name,
            on_finish=self.ShowWelcome,
        )

        self._switch_to_dynamic(panel)

    def ShowError(self, message="An unknown error occurred."):
        panel = ErrorPanel(
            parent=self.panel_content,
            error_message=message,
            on_back=self.ShowOverview,
            on_troubleshoot=self.show_troubleshooting_panel
        )
        self._switch_to_dynamic(panel)

    def CancelBuild(self):
        self.ShowOverview()

    # ---------------------------------------------------------
    # DOWNLOAD + EXTRACTION PIPELINE  (NEW PIPELINE)
    # ---------------------------------------------------------
    def start_download(self, entry, panel):
        """
        Called by DownloadInstallersPanel when user clicks Download.
        New pipeline: direct curl download via download_installer().
        """
        url = entry["url"]
        name = entry["name"]

        dest_dir = os.path.expanduser("~/Downloads/macOSInstallers")
        os.makedirs(dest_dir, exist_ok=True)

        dest = os.path.join(dest_dir, f"{name}.pkg")

        print(f"[Download] Starting: {name}")
        print(f"[Download] URL: {url}")
        print(f"[Download] Saving to: {dest}")

        try:
            # Direct download using curl
            download_installer(url, dest)

            # Update UI to 100%
            panel.update_progress(entry, 100)

            # Begin extraction
            self._extract_after_download(entry, dest, panel)

        except Exception as e:
            panel.download_error(entry, f"Download failed: {e}")

    def _extract_after_download(self, entry, pkg_path, panel):
        """
        Extracts the InstallAssistant.pkg after download completes.
        """
        try:
            row = panel.rows.get(entry["version"])
            if row:
                row["status"].SetLabel("Extracting...")

            app_path = self.extractor.extract(pkg_path, output_dir="/Applications")

            panel.download_complete(entry, app_path)

            # Refresh installer list after extraction
            self._refresh_installers()

        except Exception as e:
            panel.download_error(entry, f"Extraction failed: {e}")


    # ---------------------------------------------------------
    # Misc
    # ---------------------------------------------------------
    def _refresh_installers(self):
        self.page_installers.RefreshInstallers()
