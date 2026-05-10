# **MultiMac — Multi‑macOS USB Installer Builder**
[![Download MultiMac](https://img.shields.io/badge/Download-MultiMac-blue)](https://www.dropbox.com/scl/fi/ocpz2dk7gzoyi223patv4/MultiMac.dmg?rlkey=88hd7l9uxk4kw5o5lo61f5v4i&st=rui4agxq&dl=1))

A fast, reliable, GUI‑driven tool for creating **multiple macOS installers on a single USB drive**.  
MultiMac automatically partitions the target disk, formats each slice, and runs Apple’s official `createinstallmedia` for every macOS version you select.

Built for technicians, power users, and anyone who maintains multiple Macs.

---

## ✨ Features
- **Multi‑installer USB creation** — build 2–8 macOS installers on one drive  
- **Automatic GPT partitioning** using raw‑device access  
- **Automatic `createinstallmedia` execution** for each installer  
- **Modern Python 3.12 engine**  
- **PyInstaller‑bundled macOS app**  
- **Sudo Companion launcher** for proper elevated execution  
- **Clean, simple GUI** built with wxPython  
- **Full logging** to `~/MultiMacOSInstaller.log`

---

## 🖥️ Supported macOS Versions
MultiMac supports all macOS installers that use `createinstallmedia`, including:

- macOS Sierra  
- macOS High Sierra  
- macOS Mojave  
- macOS Catalina  
- macOS Big Sur  
- macOS Monterey  
- macOS Ventura  
- macOS Sonoma  
- macOS Sequoia  

(Additional versions can be added easily.)

---

## 🧰 Requirements
- macOS host system  
- Python not required for end‑users (PyInstaller bundle)  
- USB drive **32GB minimum** (64GB+ recommended)  
- Official macOS installer apps in `/Applications`

---

## 🚀 Installation
Download the latest release from the Releases page and place both apps in `/Applications`:

- **MultiMac.app**  
- **MultiMac Launcher.app**

The MultiMac Launcher is required because macOS GUI apps cannot self‑elevate.  
It launches MultiMac with proper root privileges.

---

## 🔧 Usage
1. Launch **MultiMac Launcher.app**  
2. Enter your administrator password  
3. MultiMac opens with full root privileges  
4. Select your macOS installers  
5. Select your target USB drive  
6. Click **Build**  
7. MultiMac will:
   - Erase the disk  
   - Create GPT partitions  
   - Format each slice  
   - Run `createinstallmedia` for each installer  

Progress and logs appear in the UI and in:

```
~/MultiMacOSInstaller.log
```

---

## 📁 Project Structure
```
MultiMac/
│
├── src/
│   ├── engine/              # Partitioning + CIM engine
│   ├── ui/                  # wxPython GUI
│   └── main.py              # App entry point
│
├── assets/                  # Icons, screenshots, banners
├── dist/                    # PyInstaller output (ignored)
├── build/                   # PyInstaller temp files (ignored)
│
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🛠️ Building From Source
Install dependencies:

```
pip install -r requirements.txt
```

Build the app:

```
pyinstaller main.spec
```

The final `.app` bundle will appear in `dist/`.

---

## 🔐 Sudo Companion - MultiMac Launcher.app
macOS does not allow GUI apps to elevate themselves.  
MultiMac uses a tiny AppleScript wrapper to launch the binary with root privileges:

```applescript
do shell script "/Applications/MultiMac.app/Contents/MacOS/MultiMac" with administrator privileges
```

This ensures:

- `gpt add`  
- `diskutil eraseVolume`  
- raw‑device access  
- `createinstallmedia`  

all run correctly.

---

## 📝 Logging
All engine logs are written to:

```
~/MultiMacOSInstaller.log
```

This includes:

- Commands executed  
- Partition layout  
- CIM output  
- Errors and tracebacks  

---

## 📄 License
MIT License (recommended).  
You can change this to any license you prefer.

---

## 🤝 Contributing
Pull requests are welcome.  
If you want to add new macOS versions, improve the UI, or enhance the engine, feel free to open an issue.

---

## 📬 Contact
For issues, feature requests, or questions, open a GitHub Issue.
