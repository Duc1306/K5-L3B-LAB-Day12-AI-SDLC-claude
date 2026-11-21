"""Chế độ `day` (TICKET-02 mục 2, Test Contract v1.1 mục 4.3–4.5): gather → quan → shop → Ngày kế.

Một lượt `day` dùng MỘT `Streams(seed)` cho mọi Ngày (luồng RNG tách theo tên nên Ngày 1 trùng mode độc lập;
các Ngày sau tiếp tục chuỗi của từng luồng) và một `IdAllocator` mới cho mỗi buổi (F1–F8, C1… mỗi buổi như mode
độc lập). Giả định ghi ở docs/clarify.md.

Xuyên Ngày: `money`, `earned`, `reputation`, cấp đã mua. Mỗi Ngày: Máu/oxy đầy theo cấp ĐANG ÁP DỤNG (sao từ cấp
đã mua lúc dựng Ngày), giỏ mới, kho dư bị bỏ sau Shop.

Thứ tự (mục 4.5):
- Dựng Ngày: `day_start` → `day_plan` → `phase_start(gather)`.
- Sau `gather_end` (kể cả ngất): dựng quán với kho bàn giao, `phase_start(quan)` CÙNG tick.
- Sau `quan_end`: dựng Shop, `phase_start(shop)` cùng tick.
- Shop: xử lý một `buy` trước cạnh `shop_done`; hết `max_ticks` bước hoạt động thì `shop_end(time)`.
  Đóng Shop: `days_completed += 1`, rồi kết thúc (`days_complete`) hoặc dựng Ngày kế ngay tick đó.
- Pha mới chỉ chạy gameplay từ bước sau.

Mỗi event trả về dạng (name, data, phase, day): event kết thúc mang pha cũ; vỏ event có thêm `day`.
"""

import copy

from ..errors import BadInput
from ..ids import IdAllocator
from ..rng import Streams
from .gather import GatherSim
from .plan import plan_for_day
from .quan import QuanSim

TICK = 60


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, seed, days=1):
        self.tuning = tuning
        self.days = days
        self.streams = Streams(seed)
        d = scenario.get("day", {})
        self.gather_tpl = scenario.get("gather", {})
        self.quan_tpl = scenario.get("quan", {})
        self.plan_override = d.get("day_plan", {})
        self.money = d.get("money", 0)
        self.earned = d.get("earned", 0)
        self.reputation = d.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = {k: v for k, v in sorted(d.get("upgrades", {}).items()) if v > 0}   # cấp đã mua
        self.active_upgrades = {}                                                           # cấp đang áp dụng
        self.day = 0
        self.days_completed = 0
        self.done = False
        self.reason = None
        self.phase = None
        self.cur = None
        self.plan = None
        self.shop_tick = 0
        self.leftover = []
        self.item_ids = IdAllocator()   # v1.2: id cá thể I1, I2… tăng xuyên pha và Ngày
        self.phase_changed = False
        self.start_events = self._start_day()   # event ở tick 0, ghi trước snapshot đầu

    # --- trạng thái cho runner --------------------------------------------------------
    @property
    def phase_tick(self):
        return self.shop_tick if self.phase == "shop" else self.cur.phase_tick

    @property
    def time_left_ticks(self):
        if self.phase == "shop":
            return max(0, int(self.tuning["shop"]["max_ticks"]) - self.shop_tick)
        return self.cur.time_left_ticks

    def snapshot(self) -> dict:
        s = self.cur.snapshot() if self.phase in ("gather", "quan") else {"stock": copy.deepcopy(self.leftover)}
        s.update({"day": self.day, "day_plan": copy.deepcopy(self.plan),
                  "upgrades": dict(self.upgrades), "active_upgrades": dict(self.active_upgrades)})
        return s

    # --- dựng các pha -----------------------------------------------------------------
    def _plan_for(self, n):
        if n in self.plan_override:
            return copy.deepcopy(self.plan_override[n])
        # v1.3 soak: kế hoạch D1–D5 lặp ở Ngày 6–10 (headless `--days` vẫn giới hạn 1..5)
        return plan_for_day(self.tuning, (n - 1) % len(self.tuning["day_plan"]) + 1)

    def _level_value(self, upgrade, field, default):
        lv = self.active_upgrades.get(upgrade, 0)
        if lv <= 0:
            return default
        for e in self.tuning["shop"]["upgrades"][upgrade]:
            if e["level"] == lv:
                return e[field]
        raise BadInput(f"không có cấp {lv} cho nâng cấp {upgrade}")

    def _start_day(self):
        self.day += 1
        self.active_upgrades = dict(self.upgrades)          # chỉ lúc dựng Ngày mới mới sao cấp đã mua
        self.plan = self._plan_for(self.day)
        g = self.tuning["gather"]
        tpl = copy.deepcopy(self.gather_tpl)
        if self.day > 1 and tpl.get("hold"):
            # Ngày đầu giữ nguyên id trong mẫu; các Ngày kế cấp id mới theo thứ tự mảng, giữ kind/fresh ban đầu
            tpl["hold"] = [dict(it, id=self.item_ids.new("I")) for it in tpl["hold"]]
        self.cur = GatherSim(self.tuning, tpl, self.streams, IdAllocator(), day=self.day,
                             hp_max=self._level_value("hp", "hp_max", g["hp_max"]),
                             oxygen_max_s=self._level_value("oxygen", "oxygen_max_s", g["oxygen_max_s"]),
                             item_ids=self.item_ids)
        self._sync_into(self.cur)
        self.phase = "gather"
        self.phase_changed = True
        return [("day_start", {}, "gather", self.day),
                ("day_plan", copy.deepcopy(self.plan), "gather", self.day),
                ("phase_start", {}, "gather", self.day)]

    def _start_quan(self, inventory):
        plan_dishes = sorted(self.plan["dishes"])
        tpl = copy.deepcopy(self.quan_tpl)
        # món của khách/bếp/tay trong mẫu phải thuộc kế hoạch Ngày (kiểm lúc mở quán, mục 4.3)
        for c in tpl.get("customers", []):
            if c.get("dish_id") not in plan_dishes:
                raise BadInput(f"Ngày {self.day}: khách {c.get('id')} gọi món ngoài kế hoạch {c.get('dish_id')!r}")
        held = [s.get("dish") for s in tpl.get("stoves", [])] + [tpl.get("hand")]
        for dish in held:
            if dish and dish.get("dish_id") not in plan_dishes:
                raise BadInput(f"Ngày {self.day}: món {dish.get('dish_id')!r} ngoài kế hoạch")
        tpl["reputation"] = self.reputation                 # uy tín giữ xuyên Ngày (scenario day cấm quan.reputation)
        self.cur = QuanSim(self.tuning, tpl, self.streams, IdAllocator(), inventory=inventory, plan_dishes=plan_dishes)
        self._sync_into(self.cur)
        self.phase = "quan"
        self.phase_changed = True
        return [("phase_start", {}, "quan", self.day)]

    def _start_shop(self):
        self.leftover = copy.deepcopy(self.cur.snapshot().get("stock", []))   # kho dư của ca (không hao ở Shop)
        self.shop_tick = 0
        self.phase = "shop"
        self.phase_changed = True
        return [("phase_start", {}, "shop", self.day)]

    def _sync_into(self, sim):
        sim.money, sim.earned, sim.reputation = self.money, self.earned, self.reputation

    def _sync_from(self, sim):
        self.money, self.earned, self.reputation = sim.money, sim.earned, sim.reputation

    # --- một bước gameplay (runner đã xử lý pause) --------------------------------------
    def step(self, inp):
        self.phase_changed = False
        if self.phase == "gather":
            evs = [(n, d, "gather", self.day) for n, d in self.cur.step(inp)]
            if self.cur.done:                                 # docked / time / fainted (kho rỗng) đều mở quán
                evs += self._start_quan(self.cur.inventory_items())
            return evs
        if self.phase == "quan":
            evs = [(n, d, "quan", self.day) for n, d in self.cur.step(inp)]
            self._sync_from(self.cur)
            if self.cur.done:
                evs += self._start_shop()
            return evs
        return self._shop_step(inp)

    def _shop_step(self, inp):
        self.shop_tick += 1
        evs = []
        if inp.buy is not None:
            evs.append(self._buy(inp.buy))
        if inp.pressed("shop_done"):
            evs.append(("shop_end", {"reason": "done"}, "shop", self.day))
        elif self.shop_tick >= int(self.tuning["shop"]["max_ticks"]):
            evs.append(("shop_end", {"reason": "time"}, "shop", self.day))
        else:
            return evs
        self.days_completed += 1
        self.leftover = []
        if self.days_completed >= self.days:
            self.done = True
            self.reason = "days_complete"
            return evs
        return evs + self._start_day()

    def _buy(self, action):
        table = self.tuning["shop"]["upgrades"]
        if action not in table:                               # lệnh không hỗ trợ / mở rộng chưa bật
            return ("buy_failed", {"action": action, "reason": "unknown"}, "shop", self.day)
        cur = self.upgrades.get(action, 0)
        nxt = next((e for e in table[action] if e["level"] == cur + 1), None)
        if nxt is None:
            return ("buy_failed", {"action": action, "reason": "max_level"}, "shop", self.day)
        if self.money < nxt["price"]:
            return ("buy_failed", {"action": action, "reason": "funds"}, "shop", self.day)
        self.money -= nxt["price"]                            # trừ money, giữ earned và điểm
        self.upgrades = dict(sorted({**self.upgrades, action: cur + 1}.items()))
        return ("bought", {"upgrade": action, "level": cur + 1, "price": nxt["price"], "money": self.money}, "shop", self.day)
