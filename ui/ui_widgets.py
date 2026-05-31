import wx
import os
from theme import apply_dark
from theme import DARK_BG, DARK_PANEL, DARK_TEXT, DARK_SUBTEXT, ACCENT_BLUE
from theme import ACCENT_BLUE as ACCENT_SELECT
from ui.events import InstallerSelectedEvent, EVT_INSTALLER_SELECTED
from engine.utils import resource_path
from wx.lib.agw.gradientbutton import GradientButton
from logic_drive import detect_drives


def load_icon(version_name):
    """
    Loads a macOS version icon from assets/icons/<normalized>.png
    """

    # Normalize to match your actual filenames
    name = (
        version_name.replace("Install macOS", "")
        .replace(" ", "")
        .strip()
        .lower()
    )

    rel_path = f"assets/icons/{name}.png"
    path = resource_path(rel_path)

    if os.path.exists(path):
        try:
            return wx.Bitmap(path, wx.BITMAP_TYPE_PNG)
        except Exception as e:
            print(f"[load_icon] wx.Bitmap failed: {e}")
            return None

    print(f"[load_icon] MISSING FILE: {path}")
    return None


# -------------------------------------------------------------
# Legacy InstallerTile (kept for compatibility)
# -------------------------------------------------------------
class InstallerTile(wx.Panel):
    def __init__(self, parent, label):
        super().__init__(parent)

        apply_dark(self)

        self.label = label
        self.detected = False
        self.version = None
        self.path = None
        self.selected = False

        self.SetBackgroundColour(DARK_PANEL)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.txt_title = wx.StaticText(self, label=label)
        self.txt_title.SetForegroundColour(DARK_TEXT)
        sizer.Add(self.txt_title, 0, wx.ALL, 5)

        self.txt_status = wx.StaticText(self, label="Not detected")
        self.txt_status.SetForegroundColour(DARK_SUBTEXT)
        sizer.Add(self.txt_status, 0, wx.ALL, 5)

        self.SetSizer(sizer)
        self.Bind(wx.EVT_LEFT_DOWN, self._toggle)

    def _toggle(self, event):
        if not self.detected:
            return

        self.selected = not self.selected
        self.SetBackgroundColour(ACCENT_SELECT if self.selected else DARK_PANEL)
        self.Refresh()

    def SetDetected(self, found, version=None, path=None):
        self.detected = found
        self.version = version
        self.path = path

        if found:
            self.txt_status.SetLabel(f"Detected ({version})")
            self.txt_status.SetForegroundColour(wx.Colour(80, 200, 120))
        else:
            self.txt_status.SetLabel("Not detected")
            self.txt_status.SetForegroundColour(DARK_SUBTEXT)

        self.Refresh()

    def Clear(self):
        self.detected = False
        self.selected = False
        self.version = None
        self.path = None

        self.SetBackgroundColour(DARK_PANEL)
        self.txt_status.SetLabel("Not detected")
        self.txt_status.SetForegroundColour(DARK_SUBTEXT)

        self.Refresh()


# -------------------------------------------------------------
# Version Tile (Icon-based macOS installer selector)
# -------------------------------------------------------------
class VersionTile(wx.Panel):
    def __init__(self, parent, version_name):
        super().__init__(parent)

        apply_dark(self)

        self.SetMinSize((150, 180))
        self.SetMaxSize((150, 180))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.version_name = version_name
        self.name = version_name
        self.installer_path = None
        self.size_bytes = 0
        self.selected = False

        outer = wx.BoxSizer(wx.VERTICAL)

        bmp = load_icon(version_name)
        if bmp:
            target_size = 96
            img = bmp.ConvertToImage()

            w, h = img.GetSize()
            if w != h:
                side = min(w, h)
                img = img.Resize((side, side), ((w - side) // 2, (h - side) // 2))

            img = img.Scale(target_size, target_size, wx.IMAGE_QUALITY_HIGH)
            bmp = wx.Bitmap(img)

            icon = wx.StaticBitmap(self, -1, bmp, size=(target_size, target_size))
            outer.Add(icon, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        lbl = wx.StaticText(self, -1, version_name)
        lbl.SetForegroundColour(DARK_TEXT)
        lbl.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        outer.Add(lbl, 0, wx.ALIGN_CENTER | wx.TOP, 8)

        self.lbl_status = wx.StaticText(self, -1, "Not found")
        self.lbl_status.SetForegroundColour(DARK_SUBTEXT)
        outer.Add(self.lbl_status, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 8)

        self.SetSizer(outer)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_click)
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._hover(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._hover(False))

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()

        w, h = self.GetSize()
        gc = wx.GraphicsContext.Create(dc)

        path = gc.CreatePath()
        radius = 16
        path.AddRoundedRectangle(0, 0, w, h, radius)

        # Dark frosted glass
        gc.SetBrush(wx.Brush(wx.Colour(60, 60, 60, 160)))
        gc.FillPath(path)

        # Subtle gradient
        gc.SetBrush(gc.CreateLinearGradientBrush(
            0, 0, 0, h,
            wx.Colour(80, 80, 80, 120),
            wx.Colour(60, 60, 60, 80)
        ))
        gc.FillPath(path)

        # Border
        gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 40), 1))
        gc.StrokePath(path)

        event.Skip()

    def _hover(self, state):
        if not self.selected:
            self.SetBackgroundColour(DARK_PANEL if state else DARK_BG)
            self.Refresh()

    def _on_click(self, event):
        if not self.installer_path:
            return

        self.selected = not self.selected
        self.SetBackgroundColour(ACCENT_SELECT if self.selected else DARK_BG)
        self.Refresh()

        if self.selected:
            wx.PostEvent(self.GetParent(), InstallerSelectedEvent(path=self.installer_path))

    def SetStatus(self, found, path=None):
        if found:
            self.lbl_status.SetLabel("Found")
            self.lbl_status.SetForegroundColour(wx.Colour(80, 200, 120))
            self.installer_path = path

            # Do NOT auto-select
            self.selected = False
            self.SetBackgroundColour(DARK_BG)

        else:
            self.lbl_status.SetLabel("Not found")
            self.lbl_status.SetForegroundColour(DARK_SUBTEXT)
            self.installer_path = None
            self.selected = False
            self.SetBackgroundColour(DARK_BG)

        self.Refresh()


# -------------------------------------------------------------
# USB Picker Widget
# -------------------------------------------------------------
class USBPickerPanel(wx.Panel):
    def __init__(self, parent, on_select=None):
        super().__init__(parent)

        apply_dark(self)

        self.on_select = on_select
        self.drives = []

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Select a USB Drive")
        title_font = title.GetFont()
        title_font.SetPointSize(14)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)

        main_sizer.Add(title, 0, wx.ALIGN_CENTER | wx.TOP, 20)

        self.drive_list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL
        )

        self.drive_list.SetBackgroundColour(DARK_PANEL)
        self.drive_list.SetTextColour(DARK_TEXT)

        self.drive_list.InsertColumn(0, "Disk", width=80)
        self.drive_list.InsertColumn(1, "Name", width=200)
        self.drive_list.InsertColumn(2, "Size", width=120)
        self.drive_list.InsertColumn(3, "Type", width=120)

        main_sizer.Add(self.drive_list, 1, wx.EXPAND | wx.ALL, 20)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.refresh_btn = wx.Button(self, label="Refresh")
        self.select_btn = wx.Button(self, label="Select Drive")

        btn_sizer.Add(self.refresh_btn, 0, wx.RIGHT, 10)
        btn_sizer.Add(self.select_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 20)
        self.SetSizer(main_sizer)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.OnRefresh)
        self.select_btn.Bind(wx.EVT_BUTTON, self.OnSelect)

        self.LoadDrives()

    def LoadDrives(self, drives=None):
        self.drive_list.DeleteAllItems()
        self.drives = []

        if drives is None:
            drives = detect_drives()

        for d in drives:
            device = d.get("device", "")
            name = d.get("name", "")
            size_bytes = d.get("size_bytes", 0)
            dtype = d.get("type", "USB")

            size_gb = round(size_bytes / (1024**3), 1)
            size_label = f"{size_gb} GB"

            # KEEP the original dict (including mount_point)
            drive_dict = d.copy()
            drive_dict["size_label"] = size_label
            drive_dict["size"] = size_bytes

            self.drives.append(drive_dict)

            index = self.drive_list.InsertItem(self.drive_list.GetItemCount(), device)
            self.drive_list.SetItem(index, 1, name)
            self.drive_list.SetItem(index, 2, size_label)
            self.drive_list.SetItem(index, 3, dtype)


    def OnRefresh(self, event):
        self.LoadDrives()

    def OnSelect(self, event):
        selected = self.drive_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Please select a USB drive.", "No Drive Selected")
            return

        drive_dict = self.drives[selected]

        if self.on_select:
            self.on_select(drive_dict)


# -------------------------------------------------------------
# Partition Preview Widget
# -------------------------------------------------------------
class PartitionPreview(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        apply_dark(self)

        self.segments = []
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetBackgroundColour(DARK_PANEL)

    def SetSegments(self, segments):
        self.segments = segments
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.Clear()

        if not self.segments:
            dc.SetTextForeground(DARK_TEXT)
            dc.DrawText("No installers selected.", 10, 10)
            return

        width, height = self.GetSize()
        bar_height = 40
        y = (height - bar_height) // 2

        total_size = sum(seg["size"] for seg in self.segments)
        x = 0

        for seg in self.segments:
            proportion = seg["size"] / total_size
            seg_width = int(width * proportion)

            dc.SetBrush(wx.Brush(seg["color"]))
            dc.SetPen(wx.Pen(seg["color"]))
            dc.DrawRectangle(x, y, seg_width, bar_height)

            label = seg["label"]
            tw, th = dc.GetTextExtent(label)
            dc.SetTextForeground(DARK_TEXT)
            dc.DrawText(label, x + (seg_width - tw) // 2, y + (bar_height - th) // 2)

            x += seg_width

class ExpandableItem(wx.Panel):
    def __init__(self, parent, title, body):
        super().__init__(parent)

        self.expanded = False

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Header button
        self.btn = wx.Button(self, label=title, style=wx.BU_EXACTFIT)
        self.btn.Bind(wx.EVT_BUTTON, self.on_toggle)
        sizer.Add(self.btn, 0, wx.EXPAND | wx.ALL, 5)

        # Body panel (hidden by default)
        self.body_panel = wx.Panel(self)
        body_sizer = wx.BoxSizer(wx.VERTICAL)

        txt = wx.StaticText(self.body_panel, label=body)
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        txt.Wrap(400)
        body_sizer.Add(txt, 0, wx.ALL, 10)

        self.body_panel.SetSizer(body_sizer)
        self.body_panel.Hide()

        sizer.Add(self.body_panel, 0, wx.EXPAND)

        self.SetSizer(sizer)

    def on_toggle(self, event):
        self.expanded = not self.expanded
        if self.expanded:
            self.body_panel.Show()
        else:
            self.body_panel.Hide()

        # Force layout update
        self.GetParent().Layout()

