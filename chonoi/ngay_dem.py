"""Chơi LIỀN MẠCH trên trình duyệt: buổi sáng (gather) → buổi tối (quán) → sáng ngày mới → … trên CÙNG một cổng.

    python3 -m chonoi.ngay_dem [--port 8000] [--seed 1] [--so-ngay N] [--nghi 4]

Module của nhóm (không sửa khung `chonoi/live.py`): một tiến trình giữ một `LiveGame` đang chạy và tự thay
bằng buổi kế tiếp khi buổi hiện tại kết thúc. Kho đi từ sáng sang tối ĐÚNG như Test Contract mục G:
gather ghi file kho khi `gather_end` (`--inventory-out`), quán đọc lại file đó (`--inventory`).

Chưa phải `--mode day` của Test Contract v1.1 (Phase 2): mỗi buổi tối vẫn là một quán độc lập
(tiền bắt đầu 0, uy tín theo tuning, chỉ có kho của sáng hôm đó). Tổng thu qua các ngày chỉ để hiển thị.
"""

import argparse
import json
import os
import sys
import tempfile
import threading
import time

from .contract import load_contract
from .errors import BadInput
from .inventory import read_inventory
from .live import LiveGame, LiveServer
from .scenario import load_scenario

NEXT = {"gather": "quan", "quan": "gather"}


class DayGame:
    """Cùng giao diện với LiveGame (state_json / set_input / restart / start / stop) để dùng chung LiveServer."""

    def __init__(self, tuning, seed=1, days=None, pause_s=4.0, workdir=None, scenario_paths=None, log=None):
        self.tuning = tuning
        self.seed = seed
        self.days = days                      # None = chơi mãi
        self.pause_s = pause_s                # nghỉ để người chơi đọc bảng kết thúc buổi
        self.workdir = workdir or tempfile.mkdtemp(prefix="chonoi-ngay-")
        self.scenario_paths = scenario_paths or {}   # chỉ để test dựng tình huống: {"gather": file, "quan": file}
        self.log = log or (lambda msg: None)  # main() truyền print; test để im
        self.day = 1
        self.total_earned = 0                 # cộng `earned` của các buổi tối (chỉ hiển thị)
        self.history = []                     # [{day, kho, earned, reputation}]
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._switch_at = None
        self._watch = None
        self.game = self._make("gather")

    # --- dựng buổi -----------------------------------------------------------------
    def kho_path(self, day=None):
        return os.path.join(self.workdir, f"kho-ngay-{day or self.day}.json")

    def _make(self, mode):
        scenario = load_scenario(self.scenario_paths.get(mode), mode, self.tuning)
        seed = self.seed + self.day - 1
        if mode == "gather":
            path = self.kho_path()
            if os.path.exists(path):
                os.remove(path)
            return LiveGame("gather", self.tuning, scenario, seed, inventory_out=path)
        return LiveGame("quan", self.tuning, scenario, seed, inventory=read_inventory(self.kho_path()))

    # --- vòng theo dõi: buổi xong -> nghỉ -> buổi kế ---------------------------------
    def start(self):
        self.game.start()
        self._watch = threading.Thread(target=self._loop, name="chonoi-ngay-dem", daemon=True)
        self._watch.start()

    def stop(self):
        self._stop.set()
        if self._watch:
            self._watch.join(timeout=2)
        with self._lock:
            self.game.stop()

    def _loop(self):
        while not self._stop.wait(0.05):
            with self._lock:
                self._maybe_switch()

    def _finished(self, g):
        with g._lock:
            return g.session.done, g.session.sim.reason, g.error

    def _maybe_switch(self):
        done, reason, error = self._finished(self.game)
        if not done or error or reason == "error":     # luật lỗi: đứng yên để người chơi thấy lỗi / bấm R
            self._switch_at = None
            return
        if self.game.mode == "gather" and not os.path.exists(self.kho_path()):
            return                                     # chờ LiveGame ghi xong file kho
        if self.days is not None and self.game.mode == "quan" and self.day >= self.days:
            return                                     # hết số ngày: giữ bảng kết thúc
        now = time.monotonic()
        if self._switch_at is None:
            self._switch_at = now + self.pause_s
            return
        if now < self._switch_at:
            return
        self._advance()

    def _advance(self):
        old = self.game
        if old.mode == "quan":
            snap = json.loads(old.state_json())
            self.total_earned += int(snap.get("earned") or 0)
            self.history.append({"day": self.day, "kho": read_inventory(self.kho_path()),
                                 "earned": snap.get("earned"), "reputation": snap.get("reputation")})
            self.day += 1
        old.stop()
        self.game = self._make(NEXT[old.mode])
        self.game.start()
        self._switch_at = None
        self.log(f"Ngày {self.day}: {'buổi sáng — lặn hái' if self.game.mode == 'gather' else 'buổi tối — mở quán'}")

    # --- API cho LiveServer handler ---------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = json.loads(self.game.state_json())
            left = None if self._switch_at is None else max(0.0, self._switch_at - time.monotonic())
            last = self.days is not None and self.day >= self.days and self.game.mode == "quan"
            snap["day"] = {"n": self.day, "total_earned": self.total_earned, "next": None if last else NEXT[self.game.mode],
                           "next_in_s": None if last else left, "days": self.days}
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        with self._lock:
            g = self.game
        g.set_input(body)

    def restart(self):
        """R: chơi lại BUỔI hiện tại (cùng kho buổi sáng nếu đang ở quán)."""
        with self._lock:
            if self.game.mode == "gather" and os.path.exists(self.kho_path()):
                os.remove(self.kho_path())
            self.game.restart()
            self._switch_at = None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.ngay_dem", description="Chơi liền mạch sáng → tối → sáng… (bản nối của nhóm, chưa phải --mode day).")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--so-ngay", dest="so_ngay", type=int, default=None, help="số ngày (mặc định chơi mãi)")
    p.add_argument("--nghi", type=float, default=4.0, help="số giây nghỉ giữa hai buổi")
    a = p.parse_args(argv)
    try:
        if a.so_ngay is not None and a.so_ngay < 1:
            raise BadInput("--so-ngay phải ≥ 1")
        game = DayGame(load_contract()["tuning"], a.seed, a.so_ngay, max(0.0, a.nghi), log=lambda m: print(m, flush=True))
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port} (đang có máy chủ khác chạy? thử --port 8765): {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chơi nối ngày-đêm, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    print(f"File kho mỗi ngày: {game.workdir}", flush=True)
    print("Ngày 1: buổi sáng — lặn hái", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
