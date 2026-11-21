"""Soak headless (TICKET-04 mục 2, Test Contract v1.3):

    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Chạy N Ngày trong MỘT tiến trình bằng chính `--mode day` của luật (`runner.Session` → `sim/day.py`), điều khiển bởi
một bot TẤT ĐỊNH (chỉ đọc snapshot, không RNG, không đồng hồ). Mỗi Ngày đi qua gather → quan → shop; kế hoạch D1–D5
lặp ở Ngày 6–10; tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và id cá thể tiếp tục xuyên suốt. Không ghi xếp hạng.

`soak.json`: `{days, days_completed, crashes, results:[{day, earned, reputation, score}], duration_s}`.
`results` lấy tại lúc Shop đóng (`shop_end`); `earned`/`reputation`/`score` là giá trị lũy kế của lượt tại tick đó.
Chỉ `duration_s` là số đo thời gian thực; mọi trường khác lặp lại đúng với cùng seed.

Mã thoát: 0 khi đạt (`days_completed == days` và `crashes == 0`), 1 khi không đạt hoặc lỗi ghi, 2 khi tham số sai.
"""

import argparse
import json
import math
import sys
import time
import traceback

from .contract import load_contract
from .errors import BadInput
from .inputs import InputState
from .runner import Session

SPOIL = 30.0


class Bot:
    """Bot tất định cho cả ba pha. Giữ trạng thái nút của bước trước để tạo CẠNH LÊN đúng luật."""

    def __init__(self, tuning):
        self.t = tuning
        self.prev = set()          # nút đang giữ ở bước trước
        self.shop_tries = set()    # nâng cấp đã thử trong Shop hiện tại (tránh lặp buy_failed)
        self.shop_day = None

    # --- tiện ích -----------------------------------------------------------------------------
    @staticmethod
    def _toward(pos, target, stop=0.0):
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        n = math.hypot(dx, dy)
        if n <= stop:
            return (0.0, 0.0)
        return (dx / n, dy / n)

    def _out(self, move=(0.0, 0.0), press=(), buy=None):
        """Trả InputState; `press` chỉ thành cạnh lên nếu bước trước KHÔNG giữ nút đó (nếu đang giữ thì nhả)."""
        held, edges = set(), set()
        for b in press:
            if b not in self.prev:
                held.add(b)
                edges.add(b)
        self.prev = held
        return InputState(move, {b: (b in held) for b in ("interact", "catch", "pause", "shop_done")}, edges, buy)

    # --- gather -------------------------------------------------------------------------------
    def _needs(self, snap):
        need = dict((snap.get("day_plan") or {}).get("ingredients", {}))
        for it in snap["hold"]:
            if it["fresh"] >= SPOIL and need.get(it["kind"], 0) > 0:
                need[it["kind"]] -= 1
        return {k: v for k, v in need.items() if v > 0}

    def gather(self, snap):
        g = self.t["gather"]
        p = snap["player"]
        pos = p["pos"]
        dock = g["dock_pos"]
        speed_ticks = 60.0 / g["swim_speed"]
        free = snap["hold_capacity"] - snap["hold_count"]
        need = self._needs(snap)
        back = math.dist(pos, dock) * speed_ticks + 3 * pos[1] * speed_ticks + 240
        # về bến: hết giờ, giỏ đầy hoặc đã đủ danh sách
        if snap["time_left_ticks"] <= back or free <= 0 or not need:
            target = [dock[0], 0.0]
            if math.dist(pos, dock) <= g["dock_radius"] - 0.5:
                return self._out(press=("interact",))
            return self._out(self._toward(pos, target))
        # oxy: dưới nước mà oxy không đủ để nổi lên an toàn thì nổi thẳng lên
        under = not p["at_surface"]
        rise = pos[1] * speed_ticks + 90
        if under and p["oxygen_ticks"] <= rise:
            return self._out((0.0, -1.0))
        # mục tiêu: nút sẵn sàng hoặc đàn cá của loài còn cần, vừa chỗ trong giỏ, gần nhất (hòa theo id)
        cands = []
        for n in snap["nodes"]:
            if n["ready"] and need.get(n["kind"], 0) > 0 and free >= g["node_yield"]:
                cands.append((math.dist(pos, n["pos"]), n["id"], "node", n))
        for f in snap["fish"]:
            if need.get(f["kind"], 0) > 0 and free >= g["fish_yield"][f["kind"]]:
                cands.append((math.dist(pos, f["pos"]), f["id"], "fish", f))
        if not cands:
            # không còn gì vừa ý: lượn mặt nước giữa bãi chờ cá/nút mọc lại
            return self._out(self._toward(pos, [50.0, 0.0], stop=1.0))
        _, _, kind, obj = min(cands, key=lambda c: (c[0], c[1]))
        d = math.dist(pos, obj["pos"])
        if kind == "node":
            if d <= g["interact_radius"] - 0.3 and p["at_surface"]:
                return self._out(press=("interact",))
            return self._out(self._toward(pos, obj["pos"]))
        if not under and p["oxygen_ticks"] < p["oxygen_max_ticks"] * 0.9:
            return self._out((0.0, 0.0))                              # ở mặt nước hít đầy oxy rồi mới lặn
        if d <= g["catch_radius"] - 0.3 and under and p["catch_cd_ticks"] == 0:
            return self._out(self._toward(pos, obj["pos"]), press=("catch",))
        return self._out(self._toward(pos, obj["pos"]))

    # --- quán ---------------------------------------------------------------------------------
    def quan(self, snap):
        pos = snap["player"]["pos"]
        reach = 1.0

        def go(target):
            if math.dist(pos, target) <= reach:
                return self._out(press=("interact",))
            return self._out(self._toward(pos, target))

        if snap.get("hand"):
            oid = snap["hand"]["order_id"]
            for tb in snap["tables"]:
                if tb["customer_id"] == oid:
                    return go(tb["pos"])
        ready = [s for s in snap["stoves"] if s["state"] == "ready"]
        if ready and not snap.get("hand"):
            return go(min(ready, key=lambda s: (math.dist(pos, s["pos"]), s["id"]))["pos"])
        waiting = [c for c in snap["customers"] if c["order_status"] == "reserved"]
        idle = [s for s in snap["stoves"] if s["state"] == "idle"]
        if waiting and idle:
            return go(min(idle, key=lambda s: (math.dist(pos, s["pos"]), s["id"]))["pos"])
        return self._out(self._toward(pos, self.t["quan"]["start_pos"], stop=0.3))

    # --- shop ---------------------------------------------------------------------------------
    def shop(self, snap):
        if self.shop_day != snap.get("day"):
            self.shop_day, self.shop_tries = snap.get("day"), set()
        table = self.t["shop"]["upgrades"]
        for up in ("hp", "oxygen"):                                     # ưu tiên Máu rồi oxy
            lv = snap["upgrades"].get(up, 0)
            nxt = next((e for e in table[up] if e["level"] == lv + 1), None)
            if nxt and snap["money"] >= nxt["price"] and (up, lv) not in self.shop_tries:
                self.shop_tries.add((up, lv))
                return self._out(buy=up)
        return self._out(press=("shop_done",))

    def act(self, snap):
        ph = snap["phase"]
        if ph == "gather":
            return self.gather(snap)
        if ph == "quan":
            return self.quan(snap)
        return self.shop(snap)


def soak(seed, days, tuning, max_ticks_per_day=30000):
    """Chạy soak trong tiến trình; trả dict kết quả (không gồm duration_s)."""
    mult = tuning["score"]["reputation_multiplier"]
    results, crashes = [], 0
    sess = None
    try:
        sess = Session("day", tuning, {}, seed, days=days)
        bot = Bot(tuning)
        limit = days * max_ticks_per_day
        while not sess.done and sess.tick < limit:
            rows = sess.step(bot.act(sess.snapshot()))
            for r in rows:
                if r["name"] == "shop_end":
                    sim = sess.sim
                    results.append({"day": r["day"], "earned": sim.earned, "reputation": sim.reputation,
                                    "score": sim.earned + mult * math.floor(sim.reputation)})
    except Exception:  # một lần lỗi là một crash; lượt dừng tại đó
        crashes += 1
        traceback.print_exc(file=sys.stderr)
    completed = sess.sim.days_completed if sess is not None else 0
    return {"days": days, "days_completed": completed, "crashes": crashes, "results": results}


def main(argv=None) -> int:
    t_start = time.perf_counter()
    p = argparse.ArgumentParser(prog="chonoi.soak", description="Soak headless N Ngày (Test Contract v1.3).")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.days < 1:
        sys.stderr.write("đầu vào sai: --days phải >= 1\n")
        return 2
    try:
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    out = soak(a.seed, a.days, tuning)
    out["duration_s"] = round(time.perf_counter() - t_start, 3)
    try:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    ok = out["days_completed"] == out["days"] and out["crashes"] == 0
    print(f"soak {'ĐẠT' if ok else 'KHÔNG ĐẠT'}: {out['days_completed']}/{out['days']} Ngày, crashes {out['crashes']}, "
          f"{out['duration_s']} s", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
