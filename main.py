import wx
import os
import sys
from ui.ui_mainframe import MainFrame



class SplashFrame(wx.Frame):
    def __init__(self):
        if hasattr(sys, '_MEIPASS'):
            base = os.path.join(sys._MEIPASS, 'assets')
        else:
            base = os.path.join(os.path.dirname(__file__), 'assets')

        splash_path = os.path.join(base, "splash_2.0.png")

        bmp = wx.Bitmap(splash_path, wx.BITMAP_TYPE_PNG)

        # SCALE SPLASH (adjust this number)
        SCALE = 0.60   # 60% size
        w = int(bmp.GetWidth() * SCALE)
        h = int(bmp.GetHeight() * SCALE)
        bmp = wx.Bitmap(bmp.ConvertToImage().Scale(w, h))

        style = wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_NONE
        super().__init__(None, style=style)

        panel = wx.Panel(self)
        wx.StaticBitmap(panel, -1, bmp)

        self.SetSize((w, h))

        # Center manually
        screen = wx.Display().GetGeometry()
        x = screen.x + (screen.width - w) // 2
        y = screen.y + (screen.height - h) // 2
        self.SetPosition((x, y))

        # Start fully transparent
        self.SetTransparent(0)
        self.Show()
        self.Raise()

        # Fade-in animation
        self.opacity = 0
        self.fade_in_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_fade_in, self.fade_in_timer)
        self.fade_in_timer.Start(10)  # 10ms per step

    def on_fade_in(self, event):
        if self.opacity < 255:
            self.opacity += 5
            self.SetTransparent(self.opacity)
        else:
            self.fade_in_timer.Stop()
            wx.CallLater(2000, self.start_fade_out)  # hold for 1 second

    def start_fade_out(self):
        self.fade_out_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_fade_out, self.fade_out_timer)
        self.fade_out_timer.Start(10)

    def on_fade_out(self, event):
        if self.opacity > 0:
            self.opacity -= 5
            self.SetTransparent(self.opacity)
        else:
            self.fade_out_timer.Stop()
            self.finish()

    def finish(self):
        self.Destroy()
        from ui.ui_mainframe import MainFrame
        frame = MainFrame(None)
        frame.Show()




class MyApp(wx.App):
    def OnInit(self):
        SplashFrame()
        return True


if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
