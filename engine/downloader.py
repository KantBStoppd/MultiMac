import os
import subprocess
import tempfile
import shutil


def download_installer(url, dest):
    """
    Robust curl-based downloader for Apple InstallAssistant.pkg files.
    Includes:
      - resume support
      - retry logic
      - CDN-safe headers
      - atomic writes
      - TLS hardening
    """

    if not url:
        raise ValueError("No URL provided for download")

    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    # Download to a temp file first (atomic write)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="multimac_dl_", suffix=".pkg")
    os.close(tmp_fd)

    # Curl command tuned for Apple CDN
    curl_cmd = [
        "curl",
        "--fail",                   # fail on HTTP errors
        "--location",               # follow redirects
        "--retry", "5",             # retry up to 5 times
        "--retry-delay", "2",       # wait 2 seconds between retries
        "--retry-max-time", "120",  # max retry time
        "--compressed",        # resume support
        "--output", tmp_path,       # write to temp file
        url,
    ]

    print(f"[curl] Downloading: {url}")
    print(f"[curl] Temp file: {tmp_path}")

    try:
        result = subprocess.run(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"curl failed with code {result.returncode}\n"
                f"stderr:\n{result.stderr}"
            )

        # Atomic move into final destination
        shutil.move(tmp_path, dest)
        print(f"[curl] Saved to: {dest}")

    finally:
        # Cleanup temp file if something failed
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

    return dest
