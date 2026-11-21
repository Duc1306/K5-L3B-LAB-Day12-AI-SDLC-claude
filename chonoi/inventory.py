"""File kho (Contract G).

v1.2 (Phase 3, hiện hành): kho CÁ THỂ `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}`.
  `id` chuỗi khác rỗng duy nhất, `kind` thuộc danh mục, `fresh` hữu hạn trong [0, 100]. Kho rỗng: `{"items": []}`.
v1.0/v1.1 (cũ): kho ĐẾM `{"items": {kind: số nguyên >= 0}}` — chỉ đọc khi contract_version < 1.2.

Bên đọc chọn schema theo `contract_version` (v1.2: file kho đếm -> mã 2).
Ghi: sắp theo id, độ tươi đủ chính xác để đọc lại; qua file tạm cùng thư mục rồi thay thế nguyên tử.
"""

import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import id_key

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung")
# v1.1 (Phase 2): thêm cá kèo và kèo nèo.
KINDS = KINDS_P1 + ("ca_keo", "keo_neo")
ITEM_KEYS = {"id", "kind", "fresh"}


def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        raise BadInput(f"contract_version không hợp lệ: {v!r}")


def uses_item_schema(contract_version) -> bool:
    return _version_tuple(contract_version) >= (1, 2)


def validate_counts(items, kinds=KINDS):
    """Schema kho đếm v1.0/v1.1."""
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def validate_item(it, name="item", kinds=KINDS) -> dict:
    if not isinstance(it, dict) or set(it) != ITEM_KEYS:
        raise BadInput(f"{name} phải là object có đúng {sorted(ITEM_KEYS)}")
    if not isinstance(it["id"], str) or not it["id"]:
        raise BadInput(f"{name}.id phải là chuỗi khác rỗng")
    if it["kind"] not in kinds:
        raise BadInput(f"{name}: nguyên liệu lạ {it['kind']!r}")
    f = it["fresh"]
    if isinstance(f, bool) or not isinstance(f, (int, float)) or not math.isfinite(f) or not 0 <= f <= 100:
        raise BadInput(f"{name}.fresh phải là số hữu hạn trong [0, 100], đang là {f!r}")
    return {"id": it["id"], "kind": it["kind"], "fresh": f}


def validate_items(items, kinds=KINDS) -> list:
    """Schema kho cá thể v1.2: mảng {id, kind, fresh}, id duy nhất."""
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể {id, kind, fresh} (contract v1.2)")
    out, seen = [], set()
    for i, it in enumerate(items):
        v = validate_item(it, f"items[{i}]", kinds)
        if v["id"] in seen:
            raise BadInput(f"items: id trùng {v['id']}")
        seen.add(v["id"])
        out.append(v)
    return out


def read_inventory(path: str, contract_version="1.2", kinds=KINDS):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if uses_item_schema(contract_version):
        return validate_items(data["items"], kinds)
    return validate_counts(data["items"], kinds)


def write_inventory(path: str, items: list):
    """Ghi kho cá thể v1.2 (mảng {id, kind, fresh}), sắp theo id."""
    items = sorted(items, key=lambda it: id_key(it["id"]))
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
