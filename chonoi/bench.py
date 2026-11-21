"""Benchmark có render (TICKET-04 mục 1, Test Contract v1.3):

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo: buổi sáng lõi (gather v1.2: độ tươi, cá bơi, Cá Sấu, hiệu ứng mặc định), Út Sen đứng yên ở bến, seed 42,
cửa sổ 1280×720. Lệnh dựng máy chủ live (CÙNG `runner.Session` như headless) rồi mở trình duyệt Chromium/Chrome/Edge
không giao diện tới `/?thu=1&bench=1&warm=3&dur=<duration>`. Trang ghi mốc `requestAnimationFrame` của từng khung:
làm nóng 3 s từ khung đầu tiên của cảnh, đo `duration` giây, rồi gửi mốc về `POST /bench`. Python tính 5 trường:

    frames      số khung trong khoảng đo (số khoảng giữa các mốc)
    measured_s  số giây thực tế từ mốc đầu tới mốc cuối của khoảng đo
    avg_fps     frames / measured_s
    p1_low_fps  1 / trung bình thời gian (giây) của max(1, ceil(0.01 × frames)) khung chậm nhất
    load_ms     ms từ lúc khởi chạy lệnh tới khung hình đầu tiên của cảnh đo

Tìm trình duyệt: `--browser`, biến `CHONOI_BROWSER`, rồi các tên/đường dẫn quen thuộc trên Linux/macOS/Windows.
`--headed` mở cửa sổ thật thay vì headless. Không có trình duyệt -> mã 1 kèm hướng dẫn (không bịa số).
"""

import time

T_LAUNCH_MS = time.time() * 1000.0  # mốc "khởi chạy" cho load_ms: trước mọi import nặng

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

from .contract import load_contract  # noqa: E402
from .errors import BadInput  # noqa: E402
from .live import LiveGame, _Handler  # noqa: E402

WARMUP_S = 3
WINDOW = (1280, 720)
MAX_BENCH_BODY = 4 * 1024 * 1024

_CANDIDATES = [
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "microsoft-edge",
    "microsoft-edge-stable", "msedge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser(explicit=None):
    for c in [explicit, os.environ.get("CHONOI_BROWSER")] + _CANDIDATES:
        if not c:
            continue
        if os.path.isfile(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def compute(ts_ms, first_epoch_ms, launch_ms=T_LAUNCH_MS):
    """Mốc khung (ms, đơn điệu) trong khoảng đo -> 5 trường bench.json."""
    if len(ts_ms) < 2:
        raise ValueError("cần ít nhất 2 mốc khung trong khoảng đo")
    deltas = [(b - a) / 1000.0 for a, b in zip(ts_ms, ts_ms[1:])]
    frames = len(deltas)
    measured = (ts_ms[-1] - ts_ms[0]) / 1000.0
    k = max(1, math.ceil(0.01 * frames))
    slow = sorted(deltas, reverse=True)[:k]
    return {
        "avg_fps": round(frames / measured, 2),
        "p1_low_fps": round(1.0 / (sum(slow) / k), 2),
        "frames": frames,
        "measured_s": round(measured, 3),
        "load_ms": int(round(first_epoch_ms - launch_ms)),
    }


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Trình duyệt bị tắt khi còn kết nối keep-alive -> ConnectionReset: không phải lỗi đo, bỏ qua."""
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)


class _BenchHandler(_Handler):
    result = None   # gán trên lớp con
    done = None

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/bench":
            return super().do_POST()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n <= MAX_BENCH_BODY:
                raise ValueError("body sai")
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(body, dict) or not isinstance(body.get("ts"), list):
                raise ValueError("thiếu ts")
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self.result.update(body)
        self.done.set()
        self._send(200, b'{"ok":true}')


def run_bench(seed, duration, browser, headed=False, timeout_extra=90):
    tuning = load_contract()["tuning"]
    game = LiveGame("gather", tuning, {}, seed)          # buổi sáng lõi, không scenario: Út Sen ở bến, không input
    result, done = {}, threading.Event()
    handler = type("BenchHandler", (_BenchHandler,), {"game": game, "result": result, "done": done})
    httpd = _QuietServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/?thu=1&bench=1&warm={WARMUP_S}&dur={duration}"
    profile = tempfile.mkdtemp(prefix="chonoi-bench-")
    args = [browser, f"--window-size={WINDOW[0]},{WINDOW[1]}", "--force-device-scale-factor=1",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={profile}",
            "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows", "--mute-audio"]
    if not headed:
        args.append("--headless=new")
    if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
        args.append("--no-sandbox")   # chạy bằng root (container CI) thì Chromium đòi tắt sandbox
    args.append(url)
    game.start()
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not done.wait(WARMUP_S + duration + timeout_extra):
            raise RuntimeError("trình duyệt không gửi kết quả đo kịp (trang không chạy hoặc bị chặn)")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        httpd.shutdown()
        httpd.server_close()
        game.stop()
        shutil.rmtree(profile, ignore_errors=True)
    return compute([float(x) for x in result["ts"]], float(result["first_epoch_ms"]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.bench", description="Benchmark có render cảnh lặn (Test Contract v1.3).")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--duration", type=float, required=True, help="số giây đo sau 3 s làm nóng")
    p.add_argument("--out", required=True)
    p.add_argument("--browser", help="đường dẫn Chromium/Chrome/Edge (mặc định: tự tìm, hoặc biến CHONOI_BROWSER)")
    p.add_argument("--headed", action="store_true", help="mở cửa sổ thật thay vì headless")
    a = p.parse_args(argv)
    if a.duration <= 0:
        sys.stderr.write("đầu vào sai: --duration phải > 0\n")
        return 2
    browser = find_browser(a.browser)
    if browser is None:
        sys.stderr.write("không tìm thấy Chromium/Chrome/Edge. Cài một trình duyệt nhân Chromium "
                         "(vd. `sudo apt install chromium`) hoặc chỉ đường dẫn bằng --browser / CHONOI_BROWSER.\n")
        return 1
    try:
        out = run_bench(a.seed, a.duration, browser, a.headed)
    except (BadInput, RuntimeError, OSError, ValueError, KeyError) as e:
        sys.stderr.write(f"bench lỗi: {e}\n")
        return 1
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f)
        f.write("\n")
    ok = out["avg_fps"] >= 60 and out["p1_low_fps"] >= 30 and out["load_ms"] <= 10000
    sys.stderr.write(f"bench: {json.dumps(out)} — mốc báo cáo (avg ≥ 60, 1% low ≥ 30, load ≤ 10 s): "
                     f"{'đạt' if ok else 'chưa đạt'} · trình duyệt {browser}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
