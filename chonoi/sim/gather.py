"""Buổi sáng — Lặn & Hái (`gather`). KHUNG: bơi, chặn mép, đồng hồ, cập bến, xuất kho.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Một bước theo PRD-0, Test Contract mục F "Gather":
  1. Đồng hồ, timer ca, hồi bắt, hồi nút (`node_regrown`, hái được ngay trong bước đó).
  2. Bơi + chặn biên, `dive` / `surface` khi đổi phía biên mặt nước (d <= surface_depth).
     Oxy theo d CUỐI bước: mặt nước +oxygen_refill_per_tick (kẹp max) và reset đếm ngạt; dưới nước −1
     (`oxygen_empty` khi từ dương về 0). Mỗi bước dưới nước kết thúc với oxy 0 tăng `zero_oxy_ticks`;
     đủ choke_interval_ticks -> −1 Máu (`choke`). Máu 0 -> bỏ giỏ LIFO (`faint`), `gather_end` fainted, kho rỗng.
  3. Cạnh `interact`: bến trước (`docked`), ngoài bến chỉ hái khi ở mặt nước (`gather` / `hold_full`).
  4. Cạnh `catch`: hết hồi chiêu và dưới nước -> đàn gần nhất (`fish_caught` / `hold_full`).
  5. Hết giờ -> `time`, giữ giỏ sau các hành động trên. Ghi kho đúng một lần do runner lo.
Giỏ `hold` theo thứ tự nhặt (mới nhất cuối), sức chứa hold_capacity. Đàn cá đứng yên ở Phase 1.
"""

import math

from ..ids import sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        if "fish" in scenario:
            src_fish = scenario["fish"]
        elif scenario.get("random_fish", True):
            src_fish = t["fish_initial"]
        else:
            src_fish = []
        # Đàn cá đứng yên ở phase này. Cá bơi / sinh thêm là việc của phase sau.
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": f.get("heading_deg", 0)} for f in src_fish]
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"]}
                     for f in sort_by_id(self.fish)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # 2. bơi + chặn mép, rồi dive / surface khi đổi phía biên mặt nước
        was_surface = self._at_surface()
        self._move(inp)
        now_surface = self._at_surface()
        if was_surface and not now_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif now_surface and not was_surface:
            events.append(("surface", {"pos": list(self.pos)}))
        # 2b. oxy theo d CUỐI bước, ngạt, ngất
        if self._oxygen_and_choke(events):
            return events  # ngất: đã phát faint + gather_end, dừng bước
        # 3. interact: bến trước, rồi hái (chỉ ở mặt nước)
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                self._harvest(events)
        # 4. bắt cá (chỉ dưới nước, hết hồi chiêu)
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not self._at_surface():
            self._catch(events)
        # 5. hết giờ: giữ giỏ sau các hành động ở trên
        if self.time_left_ticks <= 0:
            self._finish("time", events)
        return events

    # --- lát 1: oxy, ngạt, Máu, ngất ------------------------------------------
    def _oxygen_and_choke(self, events) -> bool:
        """Trả True nếu ngất (buổi sáng kết thúc trong bước này)."""
        t = self.t
        if self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
            return False
        before = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if before > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks > 0:
            return False
        # mỗi bước dưới nước kết thúc với oxy 0 (kể cả bước vừa chạm 0) tăng bộ đếm ngạt
        self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks < int(t["choke_interval_ticks"]):
            return False
        self.zero_oxy_ticks = 0
        self.hp = max(0, self.hp - 1)
        events.append(("choke", {"hp": self.hp}))
        if self.hp > 0:
            return False
        lost = list(reversed(self.hold))  # bỏ theo LIFO: nhặt sau bỏ trước
        self.hold = []
        events.append(("faint", {"cause": "choke", "lost": lost, "hp": 0}))
        self._finish("fainted", events)
        return True

    # --- lát 2: hái, bắt cá -----------------------------------------------------
    def _free(self) -> int:
        return int(self.t["hold_capacity"]) - len(self.hold)

    def _nearest(self, entities, radius):
        """Thực thể gần nhất trong bán kính (tính cả đúng mép), hòa theo id."""
        best = None
        for e in sort_by_id(entities):  # duyệt theo id: cái đầu tiên với khoảng cách nhỏ nhất thắng
            dd = math.dist(self.pos, e["pos"])
            if dd <= radius and (best is None or dd < best[0]):
                best = (dd, e)
        return best[1] if best else None

    def _harvest(self, events):
        ready = [n for n in self.nodes if n["regrow_ticks"] == 0]
        node = self._nearest(ready, self.t["interact_radius"])
        if node is None:
            return
        amount = int(self.t["node_yield"])
        free = self._free()
        if free < amount:
            events.append(("hold_full", {"action": "gather", "node_id": node["id"], "required": amount, "free": free}))
            return
        self.hold.extend([node["kind"]] * amount)
        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))

    def _catch(self, events):
        fish = self._nearest(self.fish, self.t["catch_radius"])
        if fish is None:
            return  # không có đàn trong tầm: không sự kiện, không hồi chiêu
        need = int(self.t["fish_yield"][fish["kind"]])
        free = self._free()
        if free < need:
            # giữ đàn và cooldown, không thử đàn khác
            events.append(("hold_full", {"action": "catch", "fish_id": fish["id"], "required": need, "free": free}))
            return
        self.hold.extend([fish["kind"]] * need)
        self.fish = [f for f in self.fish if f["id"] != fish["id"]]
        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
        events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": need}))

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
