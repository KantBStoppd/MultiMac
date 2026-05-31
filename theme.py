import wx

# -----------------------------
# Dark Mode Color Palette
# -----------------------------
DARK_BG = wx.Colour(28, 28, 30)        # main background
DARK_PANEL = wx.Colour(44, 44, 46)     # panel background
DARK_BORDER = wx.Colour(58, 58, 60)    # subtle borders
DARK_TEXT = wx.Colour(235, 235, 245)   # primary text
DARK_SUBTEXT = wx.Colour(160, 160, 170)
ACCENT_BLUE = wx.Colour(10, 132, 255)  # macOS blue


# -----------------------------
# Apply dark mode recursively
# -----------------------------
def apply_dark(widget):
    try:
        widget.SetBackgroundColour(DARK_BG)
        widget.SetForegroundColour(DARK_TEXT)
    except:
        pass

    for child in widget.GetChildren():
        # -----------------------------
        # StaticText
        # -----------------------------
        if isinstance(child, wx.StaticText):
            child.SetForegroundColour(DARK_TEXT)

        # -----------------------------
        # Buttons
        # -----------------------------
        elif isinstance(child, wx.Button):
            child.SetBackgroundColour(DARK_PANEL)
            child.SetForegroundColour(DARK_TEXT)
            child.SetWindowStyleFlag(wx.BORDER_NONE)

        # -----------------------------
        # ListCtrl
        # -----------------------------
        elif isinstance(child, wx.ListCtrl):
            child.SetBackgroundColour(DARK_PANEL)
            child.SetForegroundColour(DARK_TEXT)
            child.SetTextColour(DARK_TEXT)

            try:
                header_attr = wx.ItemAttr(DARK_PANEL, DARK_TEXT)
                child.SetHeaderAttr(header_attr)
            except Exception:
                pass

        # -----------------------------
        # TextCtrl
        # -----------------------------
        elif isinstance(child, wx.TextCtrl):
            child.SetBackgroundColour(DARK_PANEL)
            child.SetForegroundColour(DARK_TEXT)

        # -----------------------------
        # Nested Panels
        # -----------------------------
        elif isinstance(child, wx.Panel):
            child.SetBackgroundColour(DARK_BG)

        # -----------------------------
        # Recurse into children
        # -----------------------------
        apply_dark(child)
