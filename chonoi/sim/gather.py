"""Buổi sáng — Lặn & Hái (`gather`). Luật theo TICKET-02 mục 1.1–1.2 và Test Contract v1.1 mục 4.5.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Một bước (v1.1 mục 4.5 "Gather"):
  1. Đồng hồ, hồi bắt, giảm bất tử, hồi nút (`node_regrown`, hái được ngay trong bước đó).
  2. Bơi + chặn biên, `dive` / `surface`. Oxy theo d CUỐI bước; ngạt -1 Máu mỗi choke_interval_ticks
     (xuyên bất tử, không rơi hàng). Máu 0 -> `faint` + `gather_end(fainted)` ngay, bỏ các bước còn lại.
  3. Quái theo id (patrol / chase / recoil) rồi tối đa MỘT hit: -1 Máu, rơi floor(n × loss_ratio) hàng LIFO,
     bất tử invuln_ticks, con gây hit vào recoil từ bước sau. Máu 0 -> `faint(cause=monster)` + `gather_end`.
  4. Cạnh `interact`: bến trước (`docked`), ngoài bến chỉ hái khi ở mặt nước (`gather` / `hold_full`).
  5. Cạnh `catch`: hết hồi và dưới nước -> đàn gần nhất theo vị trí TRƯỚC khi cá bơi.
  6. Hết giờ -> `time`. Còn giờ thì cá bơi (đổi hướng ở bước bơi thứ fish_turn_ticks·k, phản xạ mép),
     rồi sinh tối đa một đàn ở phase_tick = fish_spawn_ticks·k (`fish_spawned`).
Giỏ `hold` là mảng CÁ THỂ theo thứ tự vào giỏ (mới nhất cuối), sức chứa hold_capacity (v1.2):
mỗi cá thể có id `I<n>` cấp từ `item_ids` (xuyên pha và Ngày), `fresh` 100 lúc lấy, hao 0.5/s từ bước sau
(đầu bước 1), `spoiled` một lần khi xuống dưới 30; hàng ươn vẫn chiếm ô. `lost` là mảng cá thể theo LIFO.

RNG: luồng `fish_spawn` (loài, điểm, hướng ban đầu) và `fish_turn` (đổi hướng), tách khỏi luồng khác.
`day`, `hp_max`, `oxygen_max_s` cho chế độ `day` truyền vào (bố trí quái theo Ngày, cấp nâng cấp đang áp dụng).
"""

import math

from ..ids import IdAllocator, id_key, sort_by_id
from .fresh import Freshness, item_from_json, item_to_json, items_to_json
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")
EPS = 1e-9


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, hp_max=None, oxygen_max_s=None, item_ids=None):
        t = self.t = tuning["gather"]
        self.rng = streams
        self.ids = ids
        self.fresh = Freshness(tuning)
        self.item_ids = item_ids if item_ids is not None else IdAllocator()
        self.day = day
        self.hp_max = int(hp_max if hp_max is not None else t["hp_max"])
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round((oxygen_max_s if oxygen_max_s is not None else t["oxygen_max_s"]) * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = [item_from_json(it) for it in scenario.get("hold", [])]  # thứ tự vào giỏ, cuối là mới nhất
        for it in self.hold:
            self.item_ids.reserve(it["id"])
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        # nút: scenario THAY THẾ danh sách mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        for n in self.nodes:
            ids.reserve(n["id"])
        # cá: random_fish=false tắt cá mặc định, bơi và sinh (fixture đứng yên);
        # khai `fish` khi cờ bật thì thay đàn ban đầu, vẫn bơi/sinh.
        self.fish_live = scenario.get("random_fish", True)
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": f.get("age_ticks", 0)}
                     for f in scenario.get("fish", [])]
        for f in self.fish:
            ids.reserve(f["id"])
        if "fish" not in scenario and self.fish_live:
            for _ in range(int(t["fish_initial"])):
                f = self._new_fish()
                if f is None:
                    break
                self.fish.append(f)
        # quái: scenario `monsters` thay bố trí mặc định của Ngày
        m = t["monsters"]
        if "monsters" in scenario:
            src_mon = scenario["monsters"]
        else:
            src_mon = [s for s in m["spawns"] if s["from_day"] <= day]
        self.monsters = [self._monster_from(s) for s in src_mon]
        for mo in self.monsters:
            ids.reserve(mo["id"])
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    @staticmethod
    def _monster_from(s):
        wps = [[float(c) for c in w] for w in s["waypoints"]]
        return {"id": s["id"], "kind": s["kind"], "pos": [float(c) for c in s.get("pos", wps[0])],
                "waypoints": wps, "target_idx": s.get("target_idx", 1), "state": s.get("state", "patrol"),
                "state_ticks_left": s.get("state_ticks_left", 0),
                "recoil_dir": [float(c) for c in s["recoil_dir"]] if s.get("recoil_dir") is not None else None}

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> list:
        """Kho bàn giao v1.2: mảng cá thể {id, kind, fresh} sắp theo id."""
        return items_to_json(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": items_to_json(self.hold, by_id=False), "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]} for f in sort_by_id(self.fish)],
            "monsters": [{k: mo[k] for k in ("id", "kind", "pos", "waypoints", "target_idx", "state",
                                             "state_ticks_left", "recoil_dir")} for mo in sort_by_id(self.monsters)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ, hồi chiêu, bất tử, nút mọc lại
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # 1b. độ tươi của hàng có sẵn ở đầu bước (hàng lấy trong bước này hao từ bước sau)
        self.fresh.decay(self.hold, self.fresh.gather_decay_u, "hold", events)
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
            return events
        # 3. quái theo id rồi tối đa một hit
        if self._monsters_step(events):
            return events
        # 4. interact: bến trước, rồi hái (chỉ ở mặt nước)
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                self._harvest(events)
        # 5. bắt cá (chỉ dưới nước, hết hồi chiêu), theo vị trí cá trước khi bơi
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not self._at_surface():
            self._catch(events)
        # 6. hết giờ: giữ giỏ sau các hành động ở trên; còn giờ thì cá bơi rồi sinh theo lịch
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        if self.fish_live:
            self._swim_fish()
            self._spawn_scheduled(events)
        return events

    # --- oxy, ngạt, Máu, ngất ---------------------------------------------------
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
        self.hp = max(0, self.hp - 1)  # ngạt xuyên bất tử, không làm rơi hàng
        events.append(("choke", {"hp": self.hp}))
        if self.hp > 0:
            return False
        self._faint("choke", events)
        return True

    def _faint(self, cause, events):
        lost = [item_to_json(it) for it in reversed(self.hold)]  # bỏ theo LIFO: vào sau bỏ trước
        self.hold = []
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    # --- Cá Sấu: patrol / chase / recoil, chạm ----------------------------------
    def _monsters_step(self, events) -> bool:
        """Cập nhật quái theo id rồi xét tối đa một hit. Trả True nếu ngất."""
        cfg = self.t["monsters"]
        can_hit = []
        for mo in sort_by_id(self.monsters):
            sp = cfg["species"][mo["kind"]]
            if mo["state"] == "recoil":
                step = sp["recoil_dist"] / sp["recoil_ticks"]
                mo["pos"] = self._clamp_monster([mo["pos"][0] + mo["recoil_dir"][0] * step,
                                                 mo["pos"][1] + mo["recoil_dir"][1] * step], sp)
                mo["state_ticks_left"] -= 1
                if mo["state_ticks_left"] <= 0:  # hết recoil: về patrol, xét phát hiện/chạm từ bước kế
                    mo.update(state="patrol", state_ticks_left=0, recoil_dir=None)
                continue
            deep = self.pos[1] >= sp["depths"][0]
            dd = math.dist(mo["pos"], self.pos)
            if mo["state"] == "patrol" and deep and dd <= sp["detect_radius"]:
                mo["state"] = "chase"
            elif mo["state"] == "chase" and (dd > sp["exit_radius"] or not deep):
                mo["state"] = "patrol"
            if mo["state"] == "chase":
                mo["pos"] = self._clamp_monster(_toward(mo["pos"], self.pos, sp["chase_speed"] / TICK), sp)
            else:
                target = mo["waypoints"][mo["target_idx"]]
                step = sp["patrol_speed"] / TICK
                if math.dist(mo["pos"], target) <= step + EPS:  # EPS: n bước 1/60 m cộng dồn có sai số
                    mo["pos"] = list(target)
                    mo["target_idx"] = 1 - mo["target_idx"]  # đến nơi: đổi mục tiêu cho bước sau
                else:
                    mo["pos"] = _toward(mo["pos"], target, step)
                mo["pos"] = self._clamp_monster(mo["pos"], sp)
            can_hit.append(mo)
        if self.invuln_ticks > 0:
            return False
        best = None
        for mo in can_hit:
            sp = cfg["species"][mo["kind"]]
            dd = math.dist(mo["pos"], self.pos)
            if dd <= sp["hit_radius"] and self.pos[1] >= sp["depths"][0]:
                key = (dd, id_key(mo["id"]))
                if best is None or key < best[0]:
                    best = (key, mo)
        if best is None:
            return False
        mo = best[1]
        sp = cfg["species"][mo["kind"]]
        n_lost = math.floor(len(self.hold) * cfg["loss_ratio"] + 1e-9)
        lost = [item_to_json(it) for it in reversed(self.hold[len(self.hold) - n_lost:])] if n_lost else []
        if n_lost:
            self.hold = self.hold[:len(self.hold) - n_lost]
        self.hp = max(0, self.hp - 1)
        self.invuln_ticks = int(cfg["invuln_ticks"])
        dx, dd_ = mo["pos"][0] - self.pos[0], mo["pos"][1] - self.pos[1]
        norm = math.hypot(dx, dd_)
        mo.update(state="recoil", state_ticks_left=int(sp["recoil_ticks"]),
                  recoil_dir=[dx / norm, dd_ / norm] if norm > 0 else [1.0, 0.0])
        events.append(("monster_hit", {"monster_id": mo["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp > 0:
            return False
        self._faint("monster", events)
        return True

    def _clamp_monster(self, pos, sp):
        bx = self.t["bounds"]["x"]
        lo, hi = sp["depths"]
        return [min(bx[1], max(bx[0], pos[0])), min(hi, max(lo, pos[1]))]

    # --- cá bơi và sinh ---------------------------------------------------------
    def _swim_fish(self):
        t = self.t
        step = t["fish_speed"] / TICK
        turn = int(t["fish_turn_ticks"])
        rng = self.rng.get("fish_turn")
        xlo, xhi = t["fish_x"]
        for f in sort_by_id(self.fish):
            n = f["age_ticks"] + 1  # số thứ tự bước bơi này
            if n % turn == 0:
                f["heading_deg"] = float(rng.randrange(360))
            h = f["heading_deg"]
            rad = math.radians(h)
            dlo, dhi = t["fish_depths"][f["kind"]]
            x, fx = _reflect(f["pos"][0] + math.cos(rad) * step, xlo, xhi)
            d, fd = _reflect(f["pos"][1] + math.sin(rad) * step, dlo, dhi)
            if fx:
                h = 180.0 - h  # đảo thành phần x
            if fd:
                h = -h  # đảo thành phần d
            f["heading_deg"] = h % 360.0
            f["pos"] = [x, d]
            f["age_ticks"] = n

    def _spawn_scheduled(self, events):
        t = self.t
        if self.phase_tick % int(t["fish_spawn_ticks"]) != 0 or len(self.fish) >= int(t["fish_max"]):
            return
        f = self._new_fish()
        if f is None:
            return  # hết điểm hợp lệ: bỏ lượt
        self.fish.append(f)  # cá mới tham gia bơi từ bước sau
        events.append(("fish_spawned", {"id": f["id"], "kind": f["kind"], "pos": list(f["pos"])}))

    def _new_fish(self):
        """Chọn loài theo trọng số (chuẩn hóa trên loài còn điểm cách mọi đàn > clearance), rồi điểm đều,
        rồi hướng ban đầu. Trả None nếu hết điểm. Thứ tự loài theo `fish_weights`, điểm theo x rồi d."""
        t = self.t
        rng = self.rng.get("fish_spawn")
        clear = t["fish_spawn_clearance"]
        alive = [f["pos"] for f in self.fish]
        valid = {}
        for kind, w in t["fish_weights"].items():
            if w <= 0:
                continue
            pts = [[float(x), float(d)] for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][kind]
                   if all(math.dist([x, d], p) > clear for p in alive)]
            if pts:
                valid[kind] = pts
        if not valid:
            return None
        total = sum(t["fish_weights"][k] for k in valid)
        r = rng.random() * total
        kind = None
        for k in valid:
            kind = k
            r -= t["fish_weights"][k]
            if r < 0:
                break
        pts = valid[kind]
        pos = pts[rng.randrange(len(pts))]
        heading = float(rng.randrange(360))
        return {"id": self.ids.new("F"), "kind": kind, "pos": pos, "heading_deg": heading, "age_ticks": 0}

    # --- hái, bắt cá ------------------------------------------------------------
    def _new_item(self, kind) -> dict:
        return {"id": self.item_ids.new("I"), "kind": kind, "u": self.fresh.initial_u}

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
        self.hold.extend(self._new_item(node["kind"]) for _ in range(amount))
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
        self.hold.extend(self._new_item(fish["kind"]) for _ in range(need))
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


def _toward(pos, target, step):
    """Đi tối đa `step` m về phía `target`, không vượt quá."""
    dx, dd = target[0] - pos[0], target[1] - pos[1]
    n = math.hypot(dx, dd)
    if n <= step + EPS:
        return [float(target[0]), float(target[1])]
    return [pos[0] + dx / n * step, pos[1] + dd / n * step]


def _reflect(v, lo, hi):
    """Vượt mép thì phản xạ phần quãng đường còn lại; trả (giá trị, có đảo hướng không)."""
    if v > hi:
        return max(lo, 2 * hi - v), True
    if v < lo:
        return min(hi, 2 * lo - v), True
    return v, False
