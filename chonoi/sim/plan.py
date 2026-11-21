"""Kế hoạch ngày (TICKET-02 mục 2, Test Contract v1.1 `day_plan`). Thuần dữ liệu, không phụ thuộc sim.

`dishes` là map id món -> số suất; `ingredients` = tổng công thức × số suất (tính lại, không tin số khai).
Dùng chung cho kiểm tuning (`chonoi/contract.py`), quán (lọc thực đơn theo kế hoạch) và chế độ `day` sau này.
"""

from ..errors import BadInput


def _pos_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def ingredients_for(menu: dict, dishes: dict) -> dict:
    """Tổng nguyên liệu cần cho `dishes`, sắp theo id nguyên liệu."""
    out = {}
    for dish_id, n in dishes.items():
        for kind, k in menu[dish_id]["recipe"].items():
            out[kind] = out.get(kind, 0) + k * n
    return {k: out[k] for k in sorted(out)}


def check_entry(name: str, entry: dict, menu: dict) -> dict:
    """Kiểm một mục kế hoạch {day?, dishes, ingredients?}; trả bản đã chuẩn hóa {dishes, ingredients}."""
    if not isinstance(entry, dict):
        raise BadInput(f"{name} phải là object")
    dishes = entry.get("dishes")
    if not isinstance(dishes, dict) or not dishes:
        raise BadInput(f"{name}.dishes phải là map id món -> số nguyên dương, không rỗng")
    for d, n in dishes.items():
        if d not in menu:
            raise BadInput(f"{name}.dishes: món ngoài thực đơn {d!r}")
        if not _pos_int(n):
            raise BadInput(f"{name}.dishes.{d} phải là số nguyên dương")
    need = ingredients_for(menu, dishes)
    if "ingredients" in entry:
        got = entry["ingredients"]
        if not isinstance(got, dict) or any(not _pos_int(v) for v in got.values()):
            raise BadInput(f"{name}.ingredients phải là map id nguyên liệu -> số nguyên dương")
        if dict(got) != need:
            raise BadInput(f"{name}.ingredients {got} khác tổng công thức × số suất {need}")
    return {"dishes": dict(dishes), "ingredients": need}


def plan_for_day(tuning: dict, day: int) -> dict:
    """Mục kế hoạch của Ngày `day` (1-based) từ tuning."""
    for e in tuning["day_plan"]:
        if e["day"] == day:
            return {"dishes": dict(e["dishes"]), "ingredients": ingredients_for(tuning["menu"], e["dishes"])}
    raise BadInput(f"không có kế hoạch cho Ngày {day}")
