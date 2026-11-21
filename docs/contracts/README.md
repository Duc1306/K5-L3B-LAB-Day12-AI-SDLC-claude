# Hợp đồng tích hợp (contract v1.2, Phase 3; lịch sử v1.0 → v1.2 ở mục 5)

> Nguồn gốc: PRD-0 mục D, E, G ([docs/plan/cho-noi-lab-phase-1.md](../plan/cho-noi-lab-phase-1.md)) và code đang chạy ở tag `phase-1`.
> File này **ghi lại** những gì code đang làm, không đổi hành vi. Khi muốn đổi: báo cả nhóm, ghi ADR ở `docs/adr/` và cập nhật file này **trong cùng commit** với code.

Ai giữ: Integrator. Ai bị ảnh hưởng khi đổi: `sim/gather` (ghi kho), `sim/quan` (đọc kho), `client/ui` (đọc snapshot/sự kiện), test hộp đen.

## 1. File kho (mục G) — v1.2: kho CÁ THỂ (breaking, xem [ADR-0001](../adr/0001-kho-ca-the-v12.md))

Bàn giao giữa buổi sáng và buổi tối. Gather ghi một lần khi có `gather_end`, quán đọc ở tick 0.

```json
{"items":[{"id":"I1","kind":"ca_linh","fresh":100},{"id":"I2","kind":"ca_loc","fresh":97.5}]}
```

| Quy tắc | Chi tiết | Code |
|---|---|---|
| Khóa gốc | Chỉ đúng một khóa `items`, giá trị là **mảng** cá thể. Kho rỗng `{"items":[]}`. | `chonoi/inventory.py` `read_inventory` |
| Cá thể | Đúng 3 khóa `{id, kind, fresh}`. `id` chuỗi khác rỗng, duy nhất. `kind` ∈ 6 nguyên liệu. `fresh` số hữu hạn trong [0, 100]. Sai → mã 2. | `validate_items` |
| Chọn schema | Theo `contract_version`: v1.2 chỉ nhận mảng cá thể, **file kho đếm cũ `{"items":{kind:n}}` → mã 2**. | `uses_item_schema` |
| Id | `I1`, `I2`… cấp theo thứ tự vào giỏ, tăng xuyên pha và Ngày (cả khi cá thể cũ đã dùng/bỏ). | `GatherSim(item_ids=)`, `DaySim.item_ids` |
| Byte-ổn-định | Sắp theo id, JSON gọn `(",", ":")`, UTF-8, `
` cuối. `fresh` ghi nguyên nếu chẵn, không thì float đủ chính xác để đọc lại (giữ nhánh ở ngưỡng 30). File tạm cùng thư mục rồi `os.replace`. | `write_inventory`, `sim/fresh.py` |
| Khi nào ghi | `docked`/`time`: các cá thể còn trong giỏ (kể cả hàng ươn). `fainted`: `{"items":[]}`. Chạm `--ticks` trước `gather_end`: **không** ghi. | `runner.Session.write_inventory_if_done` |
| Quán đọc | `--inventory <file>` (chỉ `--mode quan`); khai cùng `quan.stock` → mã 2. Quán nhận nguyên số lượng, id, độ tươi, kể cả hàng ươn. `stock` ở snapshot = mảng cá thể sắp theo id, **gồm cả phần khách giữ**. | `headless.py`, `sim/quan.py` |

**Độ tươi** (`tuning.freshness`): mới lấy `100`, hao từ bước sau; giỏ −0.5/s, kho quán −0.25/s (cả hàng đang giữ), kẹp 0; `fresh < 30` là ươn (vẫn chiếm ô, không nấu), phát `spoiled` đúng một lần. Pause dừng hao; món chín và hàng ở Shop không hao. Tính chính xác bằng đơn vị 1/240 điểm (`chonoi/sim/fresh.py`).

**Giữ chỗ theo id**: `customers[].reserved` là mảng id cá thể. Mỗi loại lấy cá thể khả dụng (chưa ươn, chưa ai giữ) tươi nhất, hòa theo id. Phần giữ có cá thể vừa ươn → nhả toàn bộ, giữ lại đúng một lần (theo `order_tick` rồi id bàn), thiếu → `unfulfillable`.
**Giá theo tươi**: bắt đầu nấu tiêu đúng các id đang giữ, `base_price = floor(giá × trung bình fresh / 100)`; boa `floor(base × 0.2)` trên giá đã chốt.

File mẫu hợp lệ: [`inventory.sample.json`](inventory.sample.json). Lệnh nối 2 tiến trình (smoke, kết quả ở [`docs/proof/phase-3/checks.md`](../proof/phase-3/checks.md)):

```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inputs dock-inputs.json --out g.jsonl --inventory-out kho.json
python3 -m chonoi.headless --mode quan   --seed 1 --ticks 60  --inventory kho.json --out q.jsonl
```

## 2. Giao diện `sim/*` ↔ `client/ui`

UI (`chonoi/web/index.html`) **chỉ đọc** snapshot và gửi trạng thái phím. Luật chơi chỉ nằm trong sim. Headless và live chạy chung `runner.Session`.

### 2.1 UI gửi vào (`POST /input`, `POST /restart`)

| Trường | Kiểu | Ý nghĩa | Phím |
|---|---|---|---|
| `move` | `[a, b]`, mỗi số trong [-1, 1] | gather: `[x, d]` (d dương là lặn xuống). quan: `[x, z]` | WASD / mũi tên |
| `interact` | bool (sim chỉ xét cạnh lên) | gather: cập bến / hái. quan: nấu / bưng / phục vụ | E |
| `catch` | bool (cạnh lên) | gather: bắt cá khi đang lặn | Space |
| `/restart` | — | chơi lại cùng seed và scenario | R |

Headless nhận đúng các trường này qua `--inputs` (`{"frames":[{"tick":0,"move":[1,0],"interact":true}]}`). Nút lạ (`jump`, `attack`…) thì mã 2.

### 2.2 UI được đọc (`GET /state` = snapshot JSONL + phần thêm của live)

| Nhóm | Trường |
|---|---|
| Chung | `tick`, `sim_tick`, `mode`, `phase`, `phase_tick`, `state`, `time_left_ticks`, `money`, `earned`, `reputation`, `score` |
| gather | `player{pos, vel, heading_deg, oxygen_ticks, oxygen_max_ticks, hp, hp_max, zero_oxy_ticks, invuln_ticks, catch_cd_ticks, at_surface}`, `hold[]` (theo thứ tự nhặt), `hold_count`, `hold_capacity`, `nodes[{id,pos,kind,ready,regrow_ticks}]`, `fish[{id,pos,kind,heading_deg}]` |
| quan | `player{pos, vel}`, `stock{}`, `hand` (`{order_id,dish_id,base_price}` hoặc `null`), `stoves[{id,pos,state,dish,cook_ticks_left,ready_ticks}]`, `tables[{id,pos,customer_id}]`, `customers[{id,table_id,dish_id,order_tick,state,patience_ticks_left,eat_ticks_left,order_status,reserved,base_price,tip}]` |
| Chỉ có ở live | `meta` (= `tuning[mode]`), `events[]` (các dòng event gần đây), `finished`, `reason`, `error` |

Quy ước cho UI:
- **Kho khả dụng** = `stock[k]` − tổng `customers[].reserved[k]` của các đơn `order_status == "reserved"`. UI tự tính để hiển thị, sim không xuất trường này.
- `stove.dish` là **object** payload món, không phải chuỗi.
- Trường nào chưa có thì UI bỏ qua (`?.`, `??`). UI không suy đoán luật.
- Sáng tạo hiển thị (đồ họa, thoại, nhật ký) **không** được thêm trường vào snapshot headless.

## 3. Danh sách sự kiện

Dòng event: `{"type":"event","tick":k+1,"phase":"gather|quan","name":…,"data":{…}}`, ghi theo thứ tự xử lý trong tick, trước snapshot của tick đó.

| `name` | Ai phát | `data` | Ai nghe |
|---|---|---|---|
| `gather` | `sim/gather` | `node_id`, `kind`, `amount` | UI (giỏ phồng, chữ nổi), test |
| `node_regrown` | `sim/gather` | `node_id` | UI |
| `hold_full` | `sim/gather` | `action` (`gather`/`catch`), `node_id` hoặc `fish_id`, `required`, `free` | UI (thoại "giỏ đầy") |
| `fish_caught` | `sim/gather` | `fish_id`, `kind`, `yield` | UI, test |
| `dive` / `surface` | `sim/gather` | `pos` (chỉ khi đổi phía mặt nước) | UI (bong bóng, camera) |
| `oxygen_empty` | `sim/gather` | `oxygen_ticks: 0` | UI (viền tối) |
| `choke` | `sim/gather` | `hp` sau khi trừ | UI |
| `faint` | `sim/gather` | `cause` (`choke`/`monster`), `lost[]` (**v1.2: cá thể** `{id,kind,fresh}` theo LIFO), `hp: 0` | UI, test |
| `monster_hit` | `sim/gather` | `monster_id`, `hp`, `lost[]` (cá thể, LIFO), `pos` | UI, test |
| `spoiled` (v1.2) | `sim/gather`, `sim/quan` | `item_id`, `kind`, `location` (`hold`/`stock`); một lần khi qua ngưỡng 30, nhiều cá thể thì theo id | UI (HUD ươn), test |
| `gather_end` | `sim/gather` | `reason` (`time`/`docked`/`fainted`), `inventory` (`{"items":[cá thể]}` theo mục 1) | runner (ghi kho), UI (màn chuyển), test |
| `customer_arrived` | `sim/quan` | `order_id`, `table_id`, `dish_id` | UI (bong bóng gọi món, thoại) |
| `no_dish` | `sim/quan` | `{}` (có bàn trống nhưng kho không đủ món nào) | UI |
| `cook_started` | `sim/quan` | `stove_id`, `order_id`, `dish_id`, `items[]` (**v1.2: cá thể sắp theo kind rồi id**), `base_price` (giá đã chốt theo tươi) | UI (khói bếp) |
| `dish_ready` / `dish_picked` | `sim/quan` | `stove_id`, `order_id`, `dish_id` | UI |
| `served` | `sim/quan` | `order_id`, `table_id`, `dish_id`, `patience_ticks_left`, `base_price`, `tip` | UI, test |
| `paid` | `sim/quan` | `order_id`, `table_id`, `base_price`, `tip`, `amount`, `reason` (`finished_eating`/`closing`) | UI (tiền nổi), test |
| `customer_left` | `sim/quan` | `order_id`, `table_id`, `reason` (`patience`/`closing`), `reputation` | UI (thoại bỏ về), test |
| `quan_end` | `sim/quan` | `reason: "time"`, `money`, `earned`, `shift_earned`, `reputation` | UI, test |

Dòng cuối `end`: `ticks`, `sim_tick`, `mode`, `state`, `reason` (`time`/`docked`/`fainted`/`tick_limit`), `money`, `earned`, `reputation`, `score`.

**Điểm** (mọi snapshot và `end`) = `earned + reputation_multiplier × floor(reputation)`, với `reputation_multiplier = 100` (`tuning.score`). Code ở `runner._common`.

## 4. Giả định đã chốt
Các chỗ PRD mơ hồ (giá/boa `null` trước khi chốt, họ id khách `C`, luồng RNG `customer_dish`, làm tròn uy tín 6 chữ số, `paid` không kèm `customer_left`…) ghi ở [`docs/clarify.md`](../clarify.md) mục 1–6.

## 5. Lịch sử thay đổi
| Ngày | Đổi gì | Lý do | Ai duyệt |
|---|---|---|---|
| 2026-11-21 | Viết đầy đủ hợp đồng v1.0 từ PRD-0 và code ở tag `phase-1`. Hành vi không đổi. | AC-P1-13 còn thiếu | (cả nhóm xác nhận) |
| 2026-11-21 | v1.1 (Phase 2): số chuẩn, 3 loài cá, Cá Sấu, 2 bếp/4 bàn/6 món, `day_plan`, `shop`, `day`/Shop/pause. | TICKET-02 | Duc1306, congvt |
| 2026-11-21 | **v1.2 (Phase 3, breaking)**: kho đếm → kho cá thể `{id,kind,fresh}`, `tuning.freshness`, event `spoiled`, giữ chỗ theo id, giá theo tươi, `lost`/`items` là cá thể. | TICKET-03, [ADR-0001](../adr/0001-kho-ca-the-v12.md) | Duc1306 (+ TADIZB) |
