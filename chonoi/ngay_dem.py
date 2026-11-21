"""Chơi trọn vòng ngày trên trình duyệt bằng CHÍNH chế độ `day` của luật (chonoi/sim/day.py):

    python3 -m chonoi.ngay_dem [--port 8000] [--seed 1] [--so-ngay 5] [--scenario s.json]

DayIntro → gather → EveningIntro → quán → DayResult → Shop → Ngày kế … → tổng kết (TICKET-02 mục 2).
Máy chủ dùng lại `LiveGame`/`LiveServer` của starter (không sửa `chonoi/live.py`), chỉ mở rộng:
- input v1.1: `pause`, `shop_done`, `buy` (chuỗi, một lần) ngoài `interact`/`catch`;
- snapshot có `meta` theo PHA (gather/quan) và bảng `shop` để trình duyệt vẽ Shop.
Menu, intro và kết quả Ngày do trình duyệt vẽ; trình duyệt dùng nút `pause` của luật để dừng đồng hồ khi hiện intro.
"""

import argparse
import json
import sys
import time

from .contract import load_contract
from .errors import BadInput
from .inputs import BUTTONS_V11, LiveInputs
from .live import LiveGame, LiveServer
from .runner import Session
from .scenario import load_day_scenario

LIVE_BUTTONS = ("interact", "catch", "pause", "shop_done")


class DayInputs(LiveInputs):
    """LiveInputs + `buy` (một lần, như frame headless)."""

    def __init__(self):
        super().__init__(BUTTONS_V11)
        self._buy = None

    def set(self, move=None, buy=None, **buttons):
        super().set(move, **buttons)
        if buy:
            self._buy = buy

    def advance(self):
        st = super().advance()
        st.buy, self._buy = self._buy, None
        return st


class DayLiveGame(LiveGame):
    def __init__(self, tuning, scenario, seed, days=5):
        self.days = days                      # đặt trước vì LiveGame.__init__ gọi _reset()
        super().__init__("day", tuning, scenario, seed)

    def _reset(self):
        mode, tuning, scenario, seed, _ = self._args
        self.session = Session(mode, tuning, scenario, seed, None, self.days)
        self.inputs = DayInputs()
        self.events = self.session.start_rows()   # day_start / day_plan / phase_start(gather) ở tick 0
        self._saved = True
        self.error = None

    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            ph = snap.get("phase")
            snap["meta"] = self.tuning[ph] if ph in ("gather", "quan") else {}
            snap["shop"] = self.tuning["shop"]
            snap["menu"] = self.tuning["menu"]
            snap["days"] = self.days
            snap["days_completed"] = self.session.sim.days_completed
            snap["events"] = list(self.events)
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in LIVE_BUTTONS:
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        buy = body.get("buy")
        if buy is not None and (not isinstance(buy, str) or not buy):
            raise ValueError("buy phải là chuỗi khác rỗng")
        with self._lock:
            self.inputs.set(move, buy=buy, **buttons)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.ngay_dem", description="Chơi trọn vòng ngày (chế độ day) trên trình duyệt.")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--so-ngay", dest="so_ngay", type=int, default=5, help="số Ngày (1..5, mặc định 5)")
    p.add_argument("--scenario", help="scenario của --mode day (khối day/gather/quan)")
    a = p.parse_args(argv)
    try:
        if not (1 <= a.so_ngay <= 5):
            raise BadInput("--so-ngay phải từ 1 đến 5")
        tuning = load_contract()["tuning"]
        game = DayLiveGame(tuning, load_day_scenario(a.scenario, tuning, a.so_ngay), a.seed, a.so_ngay)
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port} (đang có máy chủ khác chạy? thử --port 8765): {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chơi {a.so_ngay} Ngày, seed {a.seed}). Ctrl+C để dừng.", flush=True)
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
