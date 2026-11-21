"""Độ tươi cá thể (TICKET-03 mục 1, Test Contract v1.2). Tính CHÍNH XÁC để không lệch nhánh ở ngưỡng 30.

Bên trong sim, mỗi cá thể là `{"id", "kind", "u"}` với `u` = độ tươi × SCALE (đơn vị nguyên khi fixture biểu diễn
chính xác; nếu không thì là `Fraction`). Với SCALE = 240 và 60 tick/s: gather 0.5/s = 2 đơn vị/tick, quán
0.25/s = 1 đơn vị/tick. Ra ngoài (snapshot, event, file kho) đổi về `{"id", "kind", "fresh"}` số thực.
So ngưỡng ươn trên `u` trước khi làm tròn.
"""

from fractions import Fraction

from ..ids import id_key

SCALE = 240


def _exact(v):
    """Số JSON -> Fraction đúng như người viết (97.5 -> 195/2); int giữ int."""
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, Fraction):
        return v
    return Fraction(repr(float(v)))


def _norm(x):
    x = Fraction(x)
    return int(x) if x.denominator == 1 else x


def to_units(fresh):
    """Độ tươi -> đơn vị. Số đọc lại từ file kho (float gần nhất của k/240) được chốt về đúng k khi lệch
    < 1e-7 đơn vị (≈ 4e-10 điểm tươi), nên giá trị và nhánh ở ngưỡng 30 giữ nguyên qua bàn giao."""
    u = _exact(fresh) * SCALE
    k = round(u)
    if abs(u - k) < Fraction(1, 10_000_000):
        return int(k)
    return _norm(u)


def to_fresh(u):
    """Đơn vị -> số JSON: nguyên nếu chẵn, không thì float gần nhất (đủ chính xác để đọc lại)."""
    x = Fraction(u) / SCALE
    return int(x) if x.denominator == 1 else float(x)


class Freshness:
    """Tham số độ tươi đọc từ `tuning.freshness`."""

    def __init__(self, tuning):
        f = tuning["freshness"]
        hz = int(tuning.get("tick_hz", 60))
        self.initial_u = to_units(f["initial"])
        self.gather_decay_u = _norm(_exact(f["gather_decay_per_s"]) * SCALE / hz)
        self.quan_decay_u = _norm(_exact(f["quan_decay_per_s"]) * SCALE / hz)
        self.spoiled_below_u = to_units(f["spoiled_below"])

    def spoiled(self, item) -> bool:
        return item["u"] < self.spoiled_below_u

    def decay(self, items, per_tick, location, events):
        """Hao `per_tick` đơn vị cho mọi cá thể (kẹp 0); phát `spoiled` theo id khi đi từ >= ngưỡng xuống < ngưỡng.
        Trả danh sách id vừa ươn."""
        newly = []
        for it in sorted(items, key=lambda i: id_key(i["id"])):
            was = it["u"] >= self.spoiled_below_u
            it["u"] = max(0, it["u"] - per_tick)
            if was and it["u"] < self.spoiled_below_u:
                newly.append(it["id"])
                events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))
        return newly


def item_from_json(obj) -> dict:
    return {"id": obj["id"], "kind": obj["kind"], "u": to_units(obj["fresh"])}


def item_to_json(it) -> dict:
    return {"id": it["id"], "kind": it["kind"], "fresh": to_fresh(it["u"])}


def items_to_json(items, by_id=True) -> list:
    src = sorted(items, key=lambda i: id_key(i["id"])) if by_id else items
    return [item_to_json(i) for i in src]
