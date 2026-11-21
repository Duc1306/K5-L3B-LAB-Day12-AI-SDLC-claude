"""Đọc game.contract.json và kiểm dải hợp lệ của tuning (PRD mục 13.2; số chuẩn, khóa mới Test Contract v1.1)."""

import json
import os

from .errors import BadInput
from .inventory import KINDS
from .sim.plan import check_entry

FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"))
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if (not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos)):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _validate_gather(g):
    """Dải hợp lệ theo PRD mục 13.2 và số chuẩn v1.1."""
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")
    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or set(fy) != set(FISH_KINDS):
        raise BadInput(f"tuning.gather.fish_yield phải có đúng {list(FISH_KINDS)}")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải thuộc {list(NODE_KINDS)}")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if kinds != set(NODE_KINDS):
        raise BadInput(f"tuning.gather.nodes phải có ít nhất một nút mỗi loại {list(NODE_KINDS)}")
    _validate_fish(g, b)
    _validate_monsters(g, b)


def _range(name, v, lo, hi):
    """[a, b] với lo <= a <= b <= hi."""
    if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and lo <= v[0] <= v[1] <= hi):
        raise BadInput(f"tuning.{name} phải là [a, b] với {lo} <= a <= b <= {hi}")


def _species_map(name, m):
    if not isinstance(m, dict) or set(m) != set(FISH_KINDS):
        raise BadInput(f"tuning.{name} phải có đúng {list(FISH_KINDS)}")


def _validate_fish(g, b):
    """Cá bơi và sinh (v1.1 mục 1.1)."""
    _int_between("gather.fish_initial", g.get("fish_initial"), 0, 36)
    _int_between("gather.fish_max", g.get("fish_max"), g["fish_initial"], 36)
    _between("gather.fish_speed", g.get("fish_speed"), 0, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 100_000)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 100_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 100)
    _range("gather.fish_x", g.get("fish_x"), *b["x"])
    for key in ("fish_depths", "fish_spawn_depths"):
        _species_map(f"gather.{key}", g.get(key))
    sx = g.get("fish_spawn_x")
    if not isinstance(sx, list) or not sx or not all(_num(x) for x in sx):
        raise BadInput("tuning.gather.fish_spawn_x phải là danh sách số không rỗng")
    for k in FISH_KINDS:
        _range(f"gather.fish_depths.{k}", g["fish_depths"][k], g["surface_depth"], b["d"][1])
        lo, hi = g["fish_depths"][k]
        ds = g["fish_spawn_depths"][k]
        if not isinstance(ds, list) or not ds or not all(_num(d) and lo <= d <= hi for d in ds):
            raise BadInput(f"tuning.gather.fish_spawn_depths.{k} phải là danh sách d trong fish_depths.{k}")
    if not all(g["fish_x"][0] <= x <= g["fish_x"][1] for x in sx):
        raise BadInput("tuning.gather.fish_spawn_x phải nằm trong fish_x")
    w = g.get("fish_weights")
    _species_map("gather.fish_weights", w)
    if not all(_num(v) and v >= 0 for v in w.values()) or sum(w.values()) <= 0:
        raise BadInput("tuning.gather.fish_weights phải không âm và tổng > 0")


MONSTER_SPECIES_KEYS = {"patrol_speed", "chase_speed", "detect_radius", "exit_radius", "depths", "hit_radius",
                        "recoil_ticks", "recoil_dist"}


def _validate_monsters(g, b):
    """Cá Sấu (v1.1 mục 1.2, `gather.monsters`)."""
    m = g.get("monsters")
    if not isinstance(m, dict):
        raise BadInput("tuning.gather.monsters phải là object")
    species = m.get("species")
    if not isinstance(species, dict) or "ca_sau" not in species:
        raise BadInput("tuning.gather.monsters.species phải có ca_sau")
    for kind, sp in species.items():
        if not isinstance(sp, dict) or set(sp) != MONSTER_SPECIES_KEYS:
            raise BadInput(f"tuning.gather.monsters.species.{kind} phải có đúng {sorted(MONSTER_SPECIES_KEYS)}")
        for key in ("patrol_speed", "chase_speed", "detect_radius", "exit_radius", "hit_radius", "recoil_dist"):
            _between(f"gather.monsters.species.{kind}.{key}", sp[key], 0, 100)
        _int_between(f"gather.monsters.species.{kind}.recoil_ticks", sp["recoil_ticks"], 1, 10_000)
        _range(f"gather.monsters.species.{kind}.depths", sp["depths"], *b["d"])
    _int_between("gather.monsters.invuln_ticks", m.get("invuln_ticks"), 0, 10_000)
    ratio = m.get("loss_ratio")
    if not (_num(ratio) and 0 <= ratio <= 1):
        raise BadInput("tuning.gather.monsters.loss_ratio phải thuộc [0, 1]")
    spawns = m.get("spawns")
    if not isinstance(spawns, list):
        raise BadInput("tuning.gather.monsters.spawns phải là mảng")
    seen = set()
    for s in spawns:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or s["id"] in seen:
            raise BadInput("tuning.gather.monsters.spawns: mỗi con cần id duy nhất")
        seen.add(s["id"])
        if s.get("kind") not in species:
            raise BadInput(f"tuning.gather.monsters.spawns.{s['id']}: kind phải thuộc species")
        _int_between(f"gather.monsters.spawns.{s['id']}.from_day", s.get("from_day"), 1, 5)
        wps = s.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"tuning.gather.monsters.spawns.{s['id']}.waypoints phải có đúng 2 điểm")
        lo, hi = species[s["kind"]]["depths"]
        for i, p in enumerate([s.get("pos"), *wps]):
            _pos_in(f"gather.monsters.spawns.{s['id']}[{i}]", p, b, ("x", "d"))
            if not lo <= p[1] <= hi:
                raise BadInput(f"tuning.gather.monsters.spawns.{s['id']}: điểm ngoài dải độ sâu loài [{lo}, {hi}]")


def _validate_menu(menu):
    if not menu:
        raise BadInput("menu không được rỗng")
    for dish_id, d in menu.items():
        price, cook = d.get("price"), d.get("cook_s")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")
        r = d.get("recipe")
        if not isinstance(r, dict) or not r or any(k not in KINDS for k in r) or \
                any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in r.values()):
            raise BadInput(f"menu.{dish_id}.recipe phải là map nguyên liệu -> số nguyên dương")


def _validate_day_plan(plan, menu):
    days = [e.get("day") if isinstance(e, dict) else None for e in plan] if isinstance(plan, list) else None
    if days != [1, 2, 3, 4, 5]:
        raise BadInput("tuning.day_plan phải là mảng 5 mục với day = 1..5 theo thứ tự")
    for e in plan:
        if set(e) != {"day", "dishes", "ingredients"}:
            raise BadInput(f"tuning.day_plan[{e['day']}] phải có đúng day, dishes, ingredients")
        check_entry(f"tuning.day_plan[{e['day']}]", e, menu)


def _validate_shop(shop):
    if not isinstance(shop, dict) or set(shop) - {"max_ticks", "upgrades", "vendor"} or "upgrades" not in shop:
        raise BadInput("tuning.shop phải là {max_ticks, upgrades}")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 100_000)
    ups = shop["upgrades"]
    if not isinstance(ups, dict) or not {"oxygen", "hp"} <= set(ups):
        raise BadInput("tuning.shop.upgrades phải có oxygen và hp")
    field = {"oxygen": "oxygen_max_s", "hp": "hp_max"}
    for kind, levels in ups.items():
        if not isinstance(levels, list) or not levels:
            raise BadInput(f"tuning.shop.upgrades.{kind} phải là mảng theo cấp")
        for i, lv in enumerate(levels, 1):
            if not isinstance(lv, dict) or lv.get("level") != i:
                raise BadInput(f"tuning.shop.upgrades.{kind}: cấp phải là 1, 2, ... theo thứ tự")
            p = lv.get("price")
            if isinstance(p, bool) or not isinstance(p, int) or p <= 0:
                raise BadInput(f"tuning.shop.upgrades.{kind}[{i}].price phải là số nguyên dương")
            if kind in field and not (_num(lv.get(field[kind])) and lv[field[kind]] > 0):
                raise BadInput(f"tuning.shop.upgrades.{kind}[{i}].{field[kind]} phải > 0")


def _validate_freshness(f):
    """v1.2: độ tươi cá thể."""
    keys = {"initial", "gather_decay_per_s", "quan_decay_per_s", "spoiled_below"}
    if not isinstance(f, dict) or set(f) != keys:
        raise BadInput(f"tuning.freshness phải có đúng {sorted(keys)}")
    _between("freshness.initial", f["initial"], 0, 100)
    _between("freshness.spoiled_below", f["spoiled_below"], 0, f["initial"])
    for k in ("gather_decay_per_s", "quan_decay_per_s"):
        _between(f"freshness.{k}", f[k], 0, 100)


def validate_tuning(t):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)
    # Quán: dải hợp lệ P1 (PRD mục 13.2)
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null trong lõi (mở rộng Cháy món chưa bật)")
    for key in ("stoves", "tables"):
        arr = q.get(key)
        if not isinstance(arr, list) or not arr or len({e.get("id") for e in arr}) != len(arr):
            raise BadInput(f"tuning.quan.{key} phải là mảng không rỗng, id duy nhất")
        for e in arr:
            _pos_in(f"quan.{key}.{e['id']}.pos", e.get("pos"), q["bounds"], ("x", "z"))
    _validate_menu(menu)
    _validate_day_plan(t.get("day_plan"), menu)
    _validate_shop(t.get("shop"))
    _validate_freshness(t.get("freshness"))
