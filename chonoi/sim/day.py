"""Chế độ `day` (Test Contract v1.1): gather → quan → shop → Ngày kế, trong MỘT tiến trình.

TICKET-02 mục 2 và Test Contract v1.1 mục 4.3–4.5 "Đổi pha":
  - Dựng Ngày: `day_start` → `day_plan` → `phase_start(gather)` cùng tick (Ngày 1 ở tick 0).
    Cấp đã mua (`upgrades`) được sao sang `active_upgrades` CHỈ lúc dựng Ngày mới; oxy/Máu tối đa
    theo cấp đang áp dụng, giỏ làm mới, kho dư của Ngày trước bị bỏ.
  - Sau `gather_end` (kể cả ngất, kho rỗng) dựng quán với kho bàn giao trong bộ nhớ (schema đếm v1.0)
    và phát `phase_start(quan)` cùng tick. Quán chỉ cho khách gọi món trong kế hoạch Ngày.
  - Sau `quan_end` dựng Shop, phát `phase_start(shop)` cùng tick.
  - Sau `shop_end`: `days_completed` +1; đủ `--days` thì kết thúc `days_complete`, chưa thì dựng Ngày kế ngay.
  - Pha mới chỉ chạy gameplay từ bước sau. Event kết thúc mang pha cũ; vỏ event có thêm `day`.
Tiền, `earned`, uy tín và cấp giữ qua Ngày. Một `Streams` và một `IdAllocator` cho cả lượt
(id cá `F`, khách `C` nối tiếp xuyên Ngày).
"""

import copy

from .gather import GatherSim
from .plan import plan_for_day
from .quan import QuanSim
from .shop import ShopSim


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.rng = streams
        self.ids = ids
        self.days = days
        d = scenario["day"]
        self.templates = {"gather": scenario.get("gather", {}), "quan": scenario.get("quan", {})}
        self.plan_override = d["day_plan"]
        self.upgrades = dict(d["upgrades"])
        self.active_upgrades = {}
        self.day = 0
        self.plan = None
        self.days_completed = 0
        self.done = False
        self.reason = None
        self.cur = None
        # tiền / uy tín giữ ở đây giữa các pha; pha đang chạy giữ bản sống
        self._money, self._earned, self._reputation = d["money"], d["earned"], d["reputation"]
        self.initial_events = []  # event của tick 0 (dựng Ngày 1), runner ghi trước snapshot tick 0
        self._start_day(self.initial_events)

    # --- trạng thái chung cho runner --------------------------------------------
    @property
    def phase(self):
        return self.cur.phase

    @property
    def phase_tick(self):
        return self.cur.phase_tick

    @property
    def time_left_ticks(self):
        return self.cur.time_left_ticks

    @property
    def money(self):
        return self.cur.money

    @property
    def earned(self):
        return self.cur.earned

    @property
    def reputation(self):
        return self.cur.reputation

    def snapshot(self) -> dict:
        s = self.cur.snapshot()
        s.update({"day": self.day, "day_plan": copy.deepcopy(self.plan),
                  "upgrades": {k: self.upgrades[k] for k in sorted(self.upgrades)},
                  "active_upgrades": {k: self.active_upgrades[k] for k in sorted(self.active_upgrades)}})
        return s

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        """Trả list (name, data, phase, day): mỗi event mang pha và Ngày lúc phát."""
        out = [(n, d, self.cur.phase, self.day) for n, d in self.cur.step(inp)]
        if self.cur.done:
            self._carry()
            if self.cur.phase == "gather":
                self._open_quan(out)
            elif self.cur.phase == "quan":
                self._open_shop(out)
            else:
                self.days_completed += 1
                if self.days_completed >= self.days:
                    self.done = True
                    self.reason = "days_complete"
                else:
                    self._start_day(out)
        return out

    # --- đổi pha ------------------------------------------------------------------
    def _carry(self):
        self._money, self._earned, self._reputation = self.cur.money, self.cur.earned, self.cur.reputation

    def _emit(self, out, name, data):
        out.append((name, data, self.cur.phase, self.day))

    def _start_day(self, out):
        self.day += 1
        self.active_upgrades = dict(self.upgrades)
        self.plan = self.plan_override.get(self.day) or plan_for_day(self.tuning, self.day)
        g = GatherSim(self.tuning, copy.deepcopy(self.templates["gather"]), self.rng, self.ids,
                      day=self.day, hp_max=self._level_value("hp", "hp_max"),
                      oxygen_max_s=self._level_value("oxygen", "oxygen_max_s"))
        self._set_cur(g)
        self._emit(out, "day_start", {})
        self._emit(out, "day_plan", copy.deepcopy(self.plan))
        self._emit(out, "phase_start", {})

    def _open_quan(self, out):
        items = self.cur.inventory_items()
        q = QuanSim(self.tuning, copy.deepcopy(self.templates["quan"]), self.rng, self.ids,
                    inventory=items, plan_dishes=list(self.plan["dishes"]))
        self._set_cur(q)
        q.shift_earned = 0
        self._emit(out, "phase_start", {})

    def _open_shop(self, out):
        self._set_cur(ShopSim(self.tuning, self.cur.stock, self._money, self._earned, self._reputation,
                              self.upgrades))
        self._emit(out, "phase_start", {})

    def _set_cur(self, sim):
        sim.money, sim.earned, sim.reputation = self._money, self._earned, self._reputation
        self.cur = sim

    def _level_value(self, upgrade, field):
        """Giá trị theo cấp đang áp dụng; cấp 0 dùng số cơ sở trong tuning.gather."""
        lv = self.active_upgrades.get(upgrade, 0)
        if lv <= 0:
            return self.tuning["gather"][field]
        return self.tuning["shop"]["upgrades"][upgrade][lv - 1][field]
