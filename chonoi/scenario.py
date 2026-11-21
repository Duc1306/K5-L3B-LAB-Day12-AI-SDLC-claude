"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
Quán: kiểu/miền từng trường (khách, bếp, bàn, payload món, uy tín) ở `_validate_quan_fields`.
Mâu thuẫn cần kho đã nạp (giữ chỗ quá tồn, đơn assigned đúng một món, bếp/tay cùng đơn, eating thiếu
giá/tip...) kiểm ở `QuanSim._check_links` — PRD-0 mục D, 'Mã 2'.
"""

import json

from .errors import BadInput
from .inventory import KINDS, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "monsters", "time_left_ticks"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
FISH_KEYS = {"id", "kind", "pos", "heading_deg", "age_ticks"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
MONSTER_STATES = ("patrol", "chase", "recoil")  # `stunned` chỉ có khi bật mở rộng Lao xua
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return _load_day({}, tuning) if mode == "day" else {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if mode == "day":
        return _load_day(data, tuning)
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan", "day"}:
        raise BadInput("scenario chỉ được có khối 'gather', 'quan' hoặc 'day'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    return _load_block(data, mode, tuning)


def _load_block(data, mode, tuning) -> dict:
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


# --- chế độ `day` (Test Contract v1.1 mục 4.3) ----------------------------------------
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def _load_day(data, tuning) -> dict:
    """`day` nhận `gather`, `quan` làm mẫu khởi tạo mỗi Ngày và khối `day` dựng trạng thái xuyên Ngày.

    Trả {"day": {...}, "gather": {...}, "quan": {...}} (khối vắng là {}). Kho/khách/bếp của mẫu quán được
    kiểm trên kho thực lúc mở quán (QuanSim), không kiểm được ở đây.
    """
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan", "day"}:
        raise BadInput("scenario chỉ được có khối 'gather', 'quan' hoặc 'day'")
    out = {"gather": _load_block(data, "gather", tuning), "quan": _load_block(data, "quan", tuning)}
    for key in ("stock", "reputation"):
        if key in out["quan"]:
            raise BadInput(f"không được khai quan.{key} khi chạy day (dùng gather.hold / day.reputation)")
    out["day"] = _validate_day(data.get("day", {}), tuning)
    return out


def _validate_day(d, tuning) -> dict:
    from .sim.plan import check_entry  # tránh import vòng khi nạp module

    if not isinstance(d, dict):
        raise BadInput("khối day phải là object")
    extra = set(d) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong day: {sorted(extra)}")
    for key in ("money", "earned"):
        if key in d:
            _nonneg_int(f"day.{key}", d[key])
    money, earned = d.get("money", 0), d.get("earned", 0)
    if money > 0 and "earned" not in d:
        raise BadInput("có tiền đầu kỳ thì phải khai cả day.money và day.earned")
    if money > earned:
        raise BadInput("cần 0 ≤ day.money ≤ day.earned")
    q = tuning["quan"]
    if "reputation" in d:
        r = d["reputation"]
        if not _num(r) or not (q["reputation_min"] <= r <= q["reputation_max"]):
            raise BadInput(f"day.reputation phải trong [{q['reputation_min']}, {q['reputation_max']}]")
    shop_ups = tuning["shop"]["upgrades"]
    ups = d.get("upgrades", {})
    if not isinstance(ups, dict):
        raise BadInput("day.upgrades phải là map id nâng cấp -> cấp")
    for k, lv in ups.items():
        if k not in shop_ups:
            raise BadInput(f"day.upgrades: nâng cấp lạ/chưa bật {k!r}")
        if isinstance(lv, bool) or not isinstance(lv, int) or not (0 <= lv <= len(shop_ups[k])):
            raise BadInput(f"day.upgrades.{k} phải là số nguyên trong [0, {len(shop_ups[k])}]")
    plan = {}
    if "day_plan" in d:
        if not isinstance(d["day_plan"], list):
            raise BadInput("day.day_plan phải là mảng {day, dishes, ingredients?}")
        for e in d["day_plan"]:
            n = e.get("day") if isinstance(e, dict) else None
            if isinstance(n, bool) or not isinstance(n, int) or not (1 <= n <= 5) or n in plan:
                raise BadInput("day.day_plan: mỗi mục cần day duy nhất trong 1..5")
            if set(e) - {"day", "dishes", "ingredients"}:
                raise BadInput(f"day.day_plan[{n}]: trường lạ {sorted(set(e) - {'day', 'dishes', 'ingredients'})}")
            plan[n] = check_entry(f"day.day_plan[{n}]", e, tuning["menu"])
    return {"money": money, "earned": earned, "reputation": d.get("reputation", q["reputation_initial"]),
            "upgrades": dict(ups), "day_plan": plan}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        extra = set(f) - FISH_KEYS
        if extra:
            raise BadInput(f"fish.{f['id']}: trường lạ {sorted(extra)}")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])
    for m in b.get("monsters", []):
        _validate_monster(m, g)


def _validate_monster(m, g):
    """`gather.monsters[]` (v1.1 mục 4.3): hai waypoint, target_idx 0/1, timer dương khi recoil."""
    mid = m["id"]
    extra = set(m) - MONSTER_KEYS
    if extra:
        raise BadInput(f"monsters.{mid}: trường lạ {sorted(extra)}")
    species = g["monsters"]["species"]
    if m.get("kind") not in species:
        raise BadInput(f"monsters.{mid}.kind phải là một trong {sorted(species)}")
    lo, hi = species[m["kind"]]["depths"]
    wps = m.get("waypoints")
    if not isinstance(wps, list) or len(wps) != 2:
        raise BadInput(f"monsters.{mid}.waypoints phải có đúng 2 điểm")
    points = [("pos", m["pos"])] if "pos" in m else []
    points += [(f"waypoints[{i}]", w) for i, w in enumerate(wps)]
    for name, pt in points:
        _pos(f"monsters.{mid}.{name}", pt, g["bounds"])
        if not lo <= pt[1] <= hi:
            raise BadInput(f"monsters.{mid}.{name}: d ngoài dải độ sâu của loài [{lo}, {hi}]")
    if m.get("target_idx", 1) not in (0, 1) or isinstance(m.get("target_idx"), bool):
        raise BadInput(f"monsters.{mid}.target_idx phải là 0 hoặc 1")
    state = m.get("state", "patrol")
    if state not in MONSTER_STATES:
        raise BadInput(f"monsters.{mid}.state phải là một trong {MONSTER_STATES}")
    ticks = m.get("state_ticks_left", 0)
    _nonneg_int(f"monsters.{mid}.state_ticks_left", ticks)
    rd = m.get("recoil_dir")
    if state == "recoil":
        if ticks <= 0:
            raise BadInput(f"monsters.{mid}: recoil cần state_ticks_left > 0")
        if not (isinstance(rd, list) and len(rd) == 2 and all(_num(c) for c in rd)
                and abs(rd[0] ** 2 + rd[1] ** 2 - 1) <= 1e-6):
            raise BadInput(f"monsters.{mid}.recoil_dir phải là vector đơn vị khi recoil")
    else:
        if ticks != 0:
            raise BadInput(f"monsters.{mid}: state_ticks_left chỉ dương khi recoil")
        if rd is not None:
            raise BadInput(f"monsters.{mid}.recoil_dir phải là null khi không recoil")


def _validate_quan(b, tuning):
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        validate_items(b["stock"])
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = tuning["quan"]["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    table_ids = [c.get("table_id") for c in b.get("customers", [])]
    known = {t["id"] for t in tuning["quan"]["tables"]} | {t.get("id") for t in b.get("tables", [])}
    for c in b.get("customers", []):
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")
    _validate_quan_fields(b, tuning)


QUAN_CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left", "eat_ticks_left",
                      "order_status", "reserved", "base_price", "tip"}
QUAN_STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
QUAN_TABLE_KEYS = {"id", "pos"}
DISH_PAYLOAD_KEYS = {"order_id", "dish_id", "base_price"}


def _dish_payload(name, d, menu):
    if not isinstance(d, dict) or set(d) != DISH_PAYLOAD_KEYS:
        raise BadInput(f"{name} phải là {{order_id, dish_id, base_price}} hoặc null")
    if not isinstance(d["order_id"], str) or not d["order_id"]:
        raise BadInput(f"{name}.order_id phải là id khách")
    if d["dish_id"] not in menu:
        raise BadInput(f"{name}.dish_id ngoài thực đơn: {d['dish_id']!r}")
    if isinstance(d["base_price"], bool) or not isinstance(d["base_price"], int) or d["base_price"] <= 0:
        raise BadInput(f"{name}.base_price phải là số nguyên dương")


def _validate_quan_fields(b, tuning):
    """Kiểu và miền của từng trường quán. Liên kết khách–bếp–tay–kho kiểm ở QuanSim (cần kho đã nạp)."""
    q, menu = tuning["quan"], tuning["menu"]
    qb = q["bounds"]
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    if "reputation" in b:
        r = b["reputation"]
        if not _num(r) or not (q["reputation_min"] <= r <= q["reputation_max"]):
            raise BadInput(f"reputation phải trong [{q['reputation_min']}, {q['reputation_max']}]")
    if b.get("hand") is not None:
        _dish_payload("hand", b["hand"], menu)
    for s in b.get("stoves", []):
        extra = set(s) - QUAN_STOVE_KEYS
        if extra:
            raise BadInput(f"stoves.{s['id']}: trường lạ {sorted(extra)}")
        if "pos" in s:
            _pos(f"stoves.{s['id']}.pos", s["pos"], qb, axes=("x", "z"))
        if "state" in s and s["state"] not in ("idle", "cooking", "ready"):
            raise BadInput(f"stoves.{s['id']}.state phải là idle/cooking/ready")
        for key in ("cook_ticks_left", "ready_ticks"):
            if key in s:
                _nonneg_int(f"stoves.{s['id']}.{key}", s[key])
        if s.get("dish") is not None:
            _dish_payload(f"stoves.{s['id']}.dish", s["dish"], menu)
    for tb in b.get("tables", []):
        extra = set(tb) - QUAN_TABLE_KEYS
        if extra:
            raise BadInput(f"tables.{tb['id']}: trường lạ {sorted(extra)}")
        if "pos" in tb:
            _pos(f"tables.{tb['id']}.pos", tb["pos"], qb, axes=("x", "z"))
    for c in b.get("customers", []):
        cid = c["id"]
        extra = set(c) - QUAN_CUSTOMER_KEYS
        if extra:
            raise BadInput(f"customers.{cid}: trường lạ {sorted(extra)}")
        if c.get("dish_id") not in menu:
            raise BadInput(f"customers.{cid}.dish_id phải là món trong thực đơn")
        if "state" in c and c["state"] not in ("waiting", "eating"):
            raise BadInput(f"customers.{cid}.state phải là waiting/eating")
        if "order_status" in c and c["order_status"] not in ("reserved", "assigned", "unfulfillable", "served"):
            raise BadInput(f"customers.{cid}.order_status không hợp lệ")
        for key in ("order_tick", "patience_ticks_left", "eat_ticks_left"):
            if key in c:
                _nonneg_int(f"customers.{cid}.{key}", c[key])
        for key in ("base_price", "tip"):
            if c.get(key) is not None:
                _nonneg_int(f"customers.{cid}.{key}", c[key])
        if "reserved" in c:
            r = c["reserved"]
            if not isinstance(r, dict) or any(k not in KINDS for k in r) or \
                    any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in r.values()):
                raise BadInput(f"customers.{cid}.reserved phải là map kind -> số nguyên dương")
