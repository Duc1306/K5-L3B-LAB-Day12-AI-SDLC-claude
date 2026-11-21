"""Chơi thử liền mạch một ngày: buổi sáng (gather) rồi buổi tối (quán) trên CÙNG một cổng.

Đây là cách NỐI TẠM để chơi thử, không phải chế độ `--mode day` của Test Contract v1.1 (Phase 2).
Không sửa contract hay luật: chỉ dùng cơ chế file kho có sẵn của Phase 1
    gather --inventory-out <kho.json>  →  quan --inventory <kho.json>

Cách chạy (từ thư mục repo):
    python tools/choi_ngay_dem.py                 # 1 ngày, cổng 8000
    python tools/choi_ngay_dem.py --so-ngay 3     # chơi nối 3 ngày
    python tools/choi_ngay_dem.py --port 8765 --seed 2
Mở địa chỉ in ra; trình duyệt tự chuyển cảnh khi buổi sáng kết thúc. Ctrl+C để dừng.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHO_XEM_KET_QUA_S = 4.0   # để người chơi kịp đọc bảng kết thúc buổi sáng trước khi chuyển cảnh


def _state(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/state", timeout=1) as r:
            return json.loads(r.read())
    except (OSError, ValueError):
        return None


def _start(mode, port, seed, extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, "-m", "chonoi.live", "--mode", mode, "--port", str(port), "--seed", str(seed)] + extra
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    for _ in range(100):                       # chờ máy chủ sẵn sàng
        if proc.poll() is not None:
            raise SystemExit(f"Không chạy được chế độ {mode}:\n{proc.stderr.read()}")
        if _state(port) is not None:
            return proc
        time.sleep(0.1)
    proc.terminate()
    raise SystemExit(f"Máy chủ {mode} không phản hồi ở cổng {port}")


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _wait_finished(proc, port, mode, kho=None):
    """Chờ buổi `mode` kết thúc (và file kho được ghi nếu có). R chơi lại vẫn dùng được trong lúc chờ."""
    while True:
        if proc.poll() is not None:
            raise SystemExit(f"Máy chủ {mode} đã dừng bất ngờ:\n{proc.stderr.read()}")
        st = _state(port)
        if st and st.get("mode") == mode and st.get("finished") and (kho is None or os.path.exists(kho)):
            return st
        time.sleep(0.25)


def main():
    p = argparse.ArgumentParser(description="Chơi nối buổi sáng → buổi tối (bản nối tạm, không phải --mode day).")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--so-ngay", dest="so_ngay", type=int, default=1, help="số ngày chơi nối tiếp")
    a = p.parse_args()

    tmp = tempfile.mkdtemp(prefix="chonoi-ngay-")
    print(f"Mở trình duyệt tại http://127.0.0.1:{a.port}/  (Ctrl+C để dừng)", flush=True)
    proc = None

    def _bi_tat(*_):                           # bị tắt từ ngoài: đừng để máy chủ con chạy mồ côi
        raise KeyboardInterrupt
    for sig in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), _bi_tat)
    try:
        for ngay in range(1, a.so_ngay + 1):
            kho = os.path.join(tmp, f"kho-ngay-{ngay}.json")
            print(f"Ngày {ngay}: buổi sáng — lặn hái…", flush=True)
            proc = _start("gather", a.port, a.seed + ngay - 1, ["--inventory-out", kho])
            st = _wait_finished(proc, a.port, "gather", kho)
            with open(kho, encoding="utf-8") as f:
                print(f"  Hết buổi sáng ({st.get('reason')}). Mang về quán: {json.load(f)}", flush=True)
            time.sleep(CHO_XEM_KET_QUA_S)
            _stop(proc)
            print(f"Ngày {ngay}: buổi tối — mở quán…", flush=True)
            proc = _start("quan", a.port, a.seed + ngay - 1, ["--inventory", kho])
            st = _wait_finished(proc, a.port, "quan")
            print(f"  Hết buổi tối: tiền {st.get('money')}k, uy tín {st.get('reputation')}, điểm {st.get('score')}", flush=True)
            if ngay < a.so_ngay:
                time.sleep(CHO_XEM_KET_QUA_S)
                _stop(proc)
                proc = None
        print("Xong. Máy chủ buổi tối vẫn chạy để xem kết quả; Ctrl+C để dừng.")
        while proc and proc.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if proc and proc.poll() is None:
            _stop(proc)


if __name__ == "__main__":
    main()
