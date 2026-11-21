# Smoke tích hợp Phase 2 (v1.1): gather --inventory-out → quan --inventory

- Lệnh: `gather --seed 42 --scenario integration-dock.json --inputs integration-inputs.json --ticks 1 --inventory-out integration-kho.json` (exit 0) → `quan --seed 42 --inventory integration-kho.json --ticks 0` (exit 0)
- `gather_end`: `{"reason": "docked", "inventory": {"items": {"bong_sung": 2, "ca_keo": 2, "ca_loc": 1, "keo_neo": 1}}}`
- File kho: `{"items": {"bong_sung": 2, "ca_keo": 2, "ca_loc": 1, "keo_neo": 1}}` · quán tick 0 `stock`: `{"bong_sung": 2, "ca_keo": 2, "ca_loc": 1, "keo_neo": 1}` · bếp ['B1', 'B2'] · bàn ['T1', 'T2', 'T3', 'T4']
- **ĐẠT: True** (kho gồm cả nguyên liệu mới `ca_keo`, `keo_neo`; quán có B1–B2, T1–T4)

## Regression smoke Phase 1 (lệnh nguyên văn của PRD-0) với số chuẩn v1.1
- quán tick 0 `stock` = `{"bong_sung": 2, "ca_loc": 1}` · **ĐẠT: True**
