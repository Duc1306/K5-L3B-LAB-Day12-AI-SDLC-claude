"""Vòng tick (Contract B, mô hình tick). KHUNG — thường không cần sửa.

Thứ tự ghi: snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi snapshot (nếu tới lượt
hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`):
cả hai chạy CÙNG một lớp sim, không nhân đôi logic.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    if mode == "day":
        return DaySim(tuning, scenario, seed, days)
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    return QuanSim(tuning, scenario, streams, ids, inventory=inventory)


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    return {
        "type": "snapshot", "tick": tick, "sim_tick": sim_tick, "mode": sim.mode, "phase": sim.phase,
        "phase_tick": phase_tick, "state": state, "time_left_ticks": sim.time_left_ticks,
        "money": sim.money, "earned": sim.earned, "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick, lấy snapshot / dòng end.

    v1.1: `tick` là số bước ngoài, `sim_tick` số bước gameplay (đứng yên khi pause). Pause xử lý ở đây cho
    cả ba mode: cạnh `pause` vào/ra pause, khi đang pause bỏ qua cạnh hành động và `buy`.
    """

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False
        self.phase_changed = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def _state(self):
        return "finished" if self.sim.done else ("paused" if self.paused else "playing")

    def _phase_tick(self):
        return getattr(self.sim, "phase_tick", self.sim_tick)

    def start_rows(self) -> list:
        """Event dựng lượt ở tick 0 (chỉ `day`: day_start → day_plan → phase_start(gather)), ghi trước snapshot đầu."""
        return [self._row(0, e) for e in getattr(self.sim, "start_events", [])]

    def snapshot(self) -> dict:
        s = _common(self.sim, self.tick, self.sim_tick, self._phase_tick(), self.tuning, self._state())
        s.update(self.sim.snapshot())
        return s

    def _row(self, tick, ev):
        if self.mode == "day":
            name, data, phase, day = ev
            return {"type": "event", "tick": tick, "phase": phase, "day": day, "name": name, "data": data}
        name, data = ev
        return {"type": "event", "tick": tick, "phase": self.sim.phase, "name": name, "data": data}

    def _meta_event(self, name):
        if self.mode == "day":
            return (name, {}, self.sim.phase, self.sim.day)
        return (name, {})

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        self.tick += 1
        self.phase_changed = False
        events = []
        if inp.pressed("pause"):                         # xét cạnh pause trước (mục 4.2)
            if not self.paused:
                self.paused = True
                return [self._row(self.tick, self._meta_event("paused"))]
            self.paused = False
            events.append(self._meta_event("resumed"))   # rồi chạy gameplay ngay trong bước này
        elif self.paused:
            return []
        events += self.sim.step(inp)
        self.sim_tick += 1
        self.phase_changed = bool(getattr(self.sim, "phase_changed", False))
        return [self._row(self.tick, e) for e in events]

    def end_row(self) -> dict:
        sim = self.sim
        score = _common(sim, self.tick, self.sim_tick, 0, self.tuning, "")["score"]
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": sim.mode,
               "state": "finished" if sim.done else "playing",
               "reason": sim.reason if sim.done else "tick_limit",
               "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": score}
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.start_rows():
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done or sess.phase_changed:  # v1.1: snapshot đổi pha
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
