"""Buổi tối — Mở Quán (`quan`). Nhìn từ trên xuống, vị trí `[x, z]`.

Luật theo PRD-0, Test Contract mục F "Quán" (một bước):
  1. Đồng hồ, timer ca, nấu, ăn, kiên nhẫn; `ready_ticks` chỉ tăng cho món đã ready ở ĐẦU bước.
  2. Bếp theo id: nấu xong -> ready (`dish_ready`), `ready_ticks = 0`. `burn_s` là null (không cháy).
  3. Di chuyển, rồi tối đa MỘT interact chọn theo (khoảng cách, bếp trước bàn, id):
     bếp idle nấu đơn reserved cũ nhất (`cook_started`), bếp ready giao món cho tay trống (`dish_picked`),
     bàn nhận đúng món (`served`, chốt boa).
  4. Theo id bàn: ăn xong trả tiền (`paid`) rồi rời; còn giờ thì khách chờ hết kiên nhẫn rời (`customer_left`,
     trừ uy tín); hết ca thì trả/rời với `closing` rồi `quan_end`.
  5. Còn giờ: lượt khách theo lịch (`customer_arrived` / `no_dish`).

Phase 2 (v1.1): 2 bếp / 4 bàn / 6 món đều là dữ liệu trong game.contract.json. Trong chế độ `day`,
`plan_dishes` giới hạn món khách được gọi theo kế hoạch Ngày.

Kho `stock` là tồn VẬT LÝ (gồm cả phần khách đã giữ); khả dụng = tồn − tổng `reserved`.
Mọi số đọc từ game.contract.json; ngẫu nhiên chọn món qua luồng `Streams("customer_dish")`.
"""

import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0
CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")
STOVE_STATES = ("idle", "cooking", "ready")


def _ticks(seconds) -> int:
    return int(round(seconds * TICK))


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, plan_dishes=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        # Chế độ `day`: chỉ các món trong kế hoạch Ngày (v1.1 mục 2). Quán chạy riêng dùng cả thực đơn.
        self.plan_dishes = sorted(plan_dishes) if plan_dishes is not None else None
        self.rng = streams
        self.ids = ids
        self.patience_full = _ticks(t["patience_s"])
        self.eat_full = _ticks(t["eat_s"])
        self.interval_ticks = _ticks(t["customer_interval_s"])
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2); thiếu cả hai -> kho rỗng
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", _ticks(t["duration_s"]))
        self.phase_tick = 0
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = [self._customer_defaults(c) for c in scenario.get("customers", [])]
        self._allocate_missing_reservations(scenario.get("customers", []))
        self._check_links()
        for e in self.customers:
            ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    # --- dựng fixture ---------------------------------------------------------
    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def _customer_defaults(self, c):
        return {
            "id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
            "order_tick": c.get("order_tick", 0), "state": c.get("state", "waiting"),
            "patience_ticks_left": c.get("patience_ticks_left", self.patience_full),
            "eat_ticks_left": c.get("eat_ticks_left", 0),
            "order_status": c.get("order_status", "reserved"),
            "reserved": dict(c.get("reserved", {})),
            "base_price": c.get("base_price"), "tip": c.get("tip"),
        }

    def _allocate_missing_reservations(self, raw):
        """Đơn reserved thiếu `reserved` -> cấp theo công thức, theo order_tick rồi id bàn."""
        declared = {c["id"] for c in raw if "reserved" in c}
        todo = [c for c in self.customers if c["order_status"] == "reserved" and c["id"] not in declared]
        for c in sorted(todo, key=lambda c: (c["order_tick"], id_key(c["table_id"]))):
            recipe = self.menu[c["dish_id"]]["recipe"]
            if not self._can_reserve(recipe):
                raise BadInput(f"customers.{c['id']}: không đủ tồn để giữ chỗ {c['dish_id']}")
            c["reserved"] = dict(recipe)

    def _check_links(self):
        """Mâu thuẫn mức luật giữa khách, bếp, tay và kho (PRD-0 mục D) -> mã 2."""
        by_order = {c["id"]: c for c in self.customers}
        holders = {}  # order_id -> nơi giữ món
        for s in self.stoves:
            d = s["dish"]
            if s["state"] == "idle":
                if d is not None or s["cook_ticks_left"] != 0:
                    raise BadInput(f"stoves.{s['id']}: bếp idle không có món và không có timer")
                continue
            if d is None:
                raise BadInput(f"stoves.{s['id']}: bếp {s['state']} phải có món")
            if s["state"] == "cooking" and s["cook_ticks_left"] <= 0:
                raise BadInput(f"stoves.{s['id']}: bếp cooking cần cook_ticks_left > 0")
            if s["state"] == "ready" and s["cook_ticks_left"] != 0:
                raise BadInput(f"stoves.{s['id']}: bếp ready không còn timer nấu")
            holders.setdefault(d["order_id"], []).append(f"stove {s['id']}")
            self._check_payload(d, by_order, f"stoves.{s['id']}.dish")
        if self.hand is not None:
            holders.setdefault(self.hand["order_id"], []).append("hand")
            self._check_payload(self.hand, by_order, "hand")
        for oid, where in holders.items():
            if len(where) > 1:
                raise BadInput(f"đơn {oid} bị giữ ở nhiều nơi: {where}")
        reserved_total = {}
        for c in self.customers:
            cid, st, status = c["id"], c["state"], c["order_status"]
            if self.plan_dishes is not None and c["dish_id"] not in self.plan_dishes:
                raise BadInput(f"customers.{cid}: món {c['dish_id']} không thuộc kế hoạch Ngày")
            if c["patience_ticks_left"] > self.patience_full or c["eat_ticks_left"] > self.eat_full:
                raise BadInput(f"customers.{cid}: bộ đếm vượt mức đầy")
            if status in ("assigned", "unfulfillable", "served") and c["reserved"]:
                raise BadInput(f"customers.{cid}: đơn {status} phải có phần giữ rỗng")
            if status == "reserved" and c["reserved"] != self.menu[c["dish_id"]]["recipe"]:
                raise BadInput(f"customers.{cid}: giữ chỗ khác công thức {c['dish_id']}")
            if status == "assigned" and len(holders.get(cid, [])) != 1:
                raise BadInput(f"customers.{cid}: đơn assigned cần đúng một món ở bếp hoặc tay")
            if status != "assigned" and cid in holders:
                raise BadInput(f"customers.{cid}: chỉ đơn assigned mới có món ở bếp/tay")
            if st == "eating":
                if status != "served" or c["eat_ticks_left"] <= 0:
                    raise BadInput(f"customers.{cid}: khách eating phải served và còn timer ăn")
                if c["base_price"] is None or c["tip"] is None:
                    raise BadInput(f"customers.{cid}: khách eating phải khai base_price và tip")
            else:
                if status == "served":
                    raise BadInput(f"customers.{cid}: đơn served thì khách phải đang eating")
                if c["eat_ticks_left"] != 0:
                    raise BadInput(f"customers.{cid}: khách chưa ăn không có timer ăn")
            for k, v in c["reserved"].items():
                reserved_total[k] = reserved_total.get(k, 0) + v
        for k, v in reserved_total.items():
            if v > self.stock.get(k, 0):
                raise BadInput(f"tổng giữ chỗ {k} = {v} vượt tồn {self.stock.get(k, 0)}")

    def _check_payload(self, d, by_order, where):
        c = by_order.get(d["order_id"])
        if c is None:
            raise BadInput(f"{where}: order_id {d['order_id']} không có khách")
        if d["dish_id"] != c["dish_id"]:
            raise BadInput(f"{where}: món {d['dish_id']} không khớp đơn {c['id']} ({c['dish_id']})")

    # --- tiện ích ---------------------------------------------------------------
    def _reserved_total(self) -> dict:
        out = {}
        for c in self.customers:
            for k, v in c["reserved"].items():
                out[k] = out.get(k, 0) + v
        return out

    def _available(self) -> dict:
        res = self._reserved_total()
        return {k: self.stock.get(k, 0) - res.get(k, 0) for k in set(self.stock) | set(res)}

    def _can_reserve(self, recipe) -> bool:
        avail = self._available()
        return all(avail.get(k, 0) >= n for k, n in recipe.items())

    def _set_reputation(self, value):
        lo, hi = self.t["reputation_min"], self.t["reputation_max"]
        # làm tròn để tránh sai số dấu phẩy động làm lệch floor(reputation) trong điểm
        self.reputation = round(min(hi, max(lo, value)), 6)

    def _customer_at(self, table_id):
        for c in self.customers:
            if c["table_id"] == table_id:
                return c
        return None

    def _drop_dish_of(self, order_id):
        """Khách rời: bỏ món của đơn đang nấu, ready hoặc trên tay (nguyên liệu đã dùng không hoàn)."""
        for s in self.stoves:
            if s["dish"] is not None and s["dish"]["order_id"] == order_id:
                s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        if self.hand is not None and self.hand["order_id"] == order_id:
            self.hand = None

    # --- giao diện cho runner -------------------------------------------------
    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ và các timer
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for s in self.stoves:
            if s["state"] == "ready":
                s["ready_ticks"] += 1  # chỉ món đã ready ở đầu bước
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
        for c in self.customers:
            if c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
            else:
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
        # 2. bếp theo id: nấu xong -> ready
        for s in self.stoves:
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"], s["ready_ticks"] = "ready", 0
                events.append(("dish_ready", self._dish_data(s)))
        # 3. di chuyển rồi tối đa một interact
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        # 4. thanh toán / rời bàn / đóng ca
        closing = self.time_left_ticks <= 0
        for c in sorted(self.customers, key=lambda c: id_key(c["table_id"])):
            if c["state"] == "eating":
                if c["eat_ticks_left"] == 0:
                    self._pay(c, "finished_eating", events)
                elif closing:
                    self._pay(c, "closing", events)
            elif closing:
                self._leave(c, "closing", events)
            elif c["patience_ticks_left"] == 0:
                self._leave(c, "patience", events)
        if closing:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
            return events
        # 5. lượt khách theo lịch
        if self.random_customers and self._customer_due():
            self._spawn_customer(events)
        return events

    # --- bước 3: interact ---------------------------------------------------------
    def _interact(self, events):
        r = self.t["interact_radius"]
        cands = []
        for s in self.stoves:
            dd = math.dist(self.pos, s["pos"])
            if dd <= r:
                cands.append((dd, 0, id_key(s["id"]), "stove", s))
        for tb in self.tables:
            dd = math.dist(self.pos, tb["pos"])
            if dd <= r:
                cands.append((dd, 1, id_key(tb["id"]), "table", tb))
        if not cands:
            return
        _, _, _, kind, obj = min(cands, key=lambda x: x[:3])
        if kind == "stove":
            self._use_stove(obj, events)
        else:
            self._serve_table(obj, events)
        # đối tượng được chọn không tương tác được -> bỏ lượt (không thử đối tượng khác)

    def _dish_data(self, s):
        return {"stove_id": s["id"], "order_id": s["dish"]["order_id"], "dish_id": s["dish"]["dish_id"]}

    def _use_stove(self, s, events):
        if s["state"] == "idle":
            waiting = [c for c in self.customers if c["order_status"] == "reserved"]
            if not waiting:
                return
            c = min(waiting, key=lambda c: (c["order_tick"], id_key(c["table_id"])))
            dish = self.menu[c["dish_id"]]
            items = []
            for k in sorted(c["reserved"]):
                n = c["reserved"][k]
                self.stock[k] = self.stock.get(k, 0) - n
                items.extend([k] * n)
            c["reserved"] = {}
            c["order_status"] = "assigned"
            c["base_price"] = int(dish["price"])
            s.update(state="cooking", cook_ticks_left=_ticks(dish["cook_s"]), ready_ticks=0,
                     dish={"order_id": c["id"], "dish_id": c["dish_id"], "base_price": c["base_price"]})
            events.append(("cook_started", dict(self._dish_data(s), items=items, base_price=c["base_price"])))
        elif s["state"] == "ready" and self.hand is None:
            data = self._dish_data(s)
            self.hand = s["dish"]
            s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
            events.append(("dish_picked", data))

    def _serve_table(self, tb, events):
        c = self._customer_at(tb["id"])
        if c is None or c["state"] != "waiting" or self.hand is None or self.hand["order_id"] != c["id"]:
            return
        base = int(self.hand["base_price"])
        ratio = c["patience_ticks_left"] / self.patience_full
        tip = math.floor(base * self.t["tip_rate"] + 1e-9) if ratio >= self.t["tip_min_patience_ratio"] else 0
        self.hand = None
        c.update(state="eating", order_status="served", eat_ticks_left=self.eat_full, base_price=base, tip=tip)
        events.append(("served", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                                  "patience_ticks_left": c["patience_ticks_left"], "base_price": base, "tip": tip}))

    # --- bước 4: tiền và rời bàn ---------------------------------------------------
    def _pay(self, c, reason, events):
        amount = c["base_price"] + c["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if c["tip"] > 0:
            self._set_reputation(self.reputation + self.t["tip_reputation"])
        self.customers.remove(c)
        events.append(("paid", {"order_id": c["id"], "table_id": c["table_id"], "base_price": c["base_price"],
                                "tip": c["tip"], "amount": amount, "reason": reason}))

    def _leave(self, c, reason, events):
        if reason == "patience":
            self._set_reputation(self.reputation + self.t["left_reputation_delta"])
        self._drop_dish_of(c["id"])
        self.customers.remove(c)  # nhả phần giữ thô: tồn vật lý không đổi, khả dụng tăng lại
        events.append(("customer_left", {"order_id": c["id"], "table_id": c["table_id"], "reason": reason,
                                         "reputation": self.reputation}))

    # --- bước 5: khách mới ---------------------------------------------------------
    def _customer_due(self) -> bool:
        first = int(self.t["first_customer_tick"])
        k = self.phase_tick - first
        return k == 0 or (k > 0 and k % self.interval_ticks == 0)

    def _spawn_customer(self, events):
        busy = {c["table_id"] for c in self.customers}
        free = [tb for tb in self.tables if tb["id"] not in busy]  # self.tables đã sắp theo id
        if not free:
            return
        table = free[0]
        # lọc theo kế hoạch (nếu có) TRƯỚC, rồi theo nguyên liệu khả dụng (v1.1 mục 4.5 "Quán")
        menu_ids = self.plan_dishes if self.plan_dishes is not None else sorted(self.menu)
        options = [d for d in menu_ids if self._can_reserve(self.menu[d]["recipe"])]
        if not options:
            events.append(("no_dish", {}))
            return
        dish_id = options[self.rng.get("customer_dish").randrange(len(options))]
        cid = self.ids.new("C")
        self.customers.append({
            "id": cid, "table_id": table["id"], "dish_id": dish_id, "order_tick": self.phase_tick,
            "state": "waiting", "patience_ticks_left": self.patience_full, "eat_ticks_left": 0,
            "order_status": "reserved", "reserved": dict(self.menu[dish_id]["recipe"]),
            "base_price": None, "tip": None,
        })
        events.append(("customer_arrived", {"order_id": cid, "table_id": table["id"], "dish_id": dish_id}))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
