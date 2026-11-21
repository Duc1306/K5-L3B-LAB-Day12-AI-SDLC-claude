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
| `dish_burnt` (mở rộng `burn`) | `sim/quan` | `stove_id`, `order_id`, `dish_id`, `order_status` sau xử lý (`reserved` nếu giữ lại được, `unfulfillable` nếu thiếu) | UI (khói, chữ "cháy món!"), test |
| `served` | `sim/quan` | `order_id`, `table_id`, `dish_id`, `patience_ticks_left`, `base_price`, `tip` | UI, test |
| `paid` | `sim/quan` | `order_id`, `table_id`, `base_price`, `tip`, `amount`, `reason` (`finished_eating`/`closing`) | UI (tiền nổi), test |
| `customer_left` | `sim/quan` | `order_id`, `table_id`, `reason` (`patience`/`closing`), `reputation` | UI (thoại bỏ về), test |
| `quan_end` | `sim/quan` | `reason: "time"`, `money`, `earned`, `shift_earned`, `reputation` | UI, test |

Dòng cuối `end`: `ticks`, `sim_tick`, `mode`, `state`, `reason` (`time`/`docked`/`fainted`/`tick_limit`), `money`, `earned`, `reputation`, `score`.

**Điểm** (mọi snapshot và `end`) = `earned + reputation_multiplier × floor(reputation)`, với `reputation_multiplier = 100` (`tuning.score`). Code ở `runner._common`.

### 3.1 Mở rộng đã bật: Cháy món (`burn`)

Manifest: `"extensions": ["burn"]` ở gốc, `tuning.quan.burn_s: 20`. `chonoi/contract.py` (`validate_extensions`) bắt
buộc hai chỗ này khớp nhau và từ chối mã mở rộng chưa làm (mã 2). Luật ở `chonoi/sim/quan.py` (`_burn`), test ở
`tests/test_ext_burn.py`.

| Quy tắc | Chi tiết |
|---|---|
| Khi nào cháy | Bước 2 của quán, theo id bếp, **trước** di chuyển và tương tác: bếp `ready` có `ready_ticks > burn_s × 60` (1200). Đúng 1200 vẫn bưng được. |
| Hậu quả | Bỏ món, nguyên liệu đã tiêu lúc nấu không hoàn, bếp `idle` ngay. Đơn của món: `base_price` về `null`, thử giữ lại ngay (tươi nhất, hòa theo id): đủ → `reserved`, thiếu → `unfulfillable`, khách vẫn chờ tới hết kiên nhẫn. |
| Không cháy | Món trên tay; món đang nấu. |
| Scenario | `quan.stoves[].ready_ticks` dựng tuổi món chín (đã có từ v1.0). |
| Snapshot | Không thêm trường. UI thấy qua event `dish_burnt` và bếp chuyển `idle`. |

## 3b. Chế độ `day`, Shop, pause (v1.1, kho theo v1.2)

- **CLI:** `--mode day [--days 1..5]` (mặc định 1). Kho bàn giao trong bộ nhớ. `--inventory`/`--inventory-out` với `day` → mã 2.
- **Vòng ngày:** `day_start` → `day_plan{dishes,ingredients}` → `phase_start` (gather) → `gather_end` → `phase_start` (quan, cùng tick) → `quan_end` → `phase_start` (shop, cùng tick) → `shop_end{reason: done|time}` → Ngày kế (cùng tick) hoặc kết thúc `days_complete`.
- **Vỏ event** có thêm `day`. Event kết thúc mang pha cũ.
- **Snapshot đổi pha:** ngoài nhịp `--snapshot-every`, runner ghi thêm một snapshot ở tick đổi pha (gather→quan, quan→shop, shop→Ngày kế) với pha mới và `phase_tick: 0`; mỗi tick vẫn tối đa một snapshot (clarify #18).
- **RNG và id:** một `Streams(seed)` cho cả lượt; id cá `F` và khách `C` cấp lại mỗi buổi; id cá thể `I` tăng xuyên pha và Ngày (clarify #17, #28).
- **Snapshot** mọi pha có thêm `day`, `day_plan`, `upgrades` (cấp đã mua), `active_upgrades` (cấp đang áp dụng). Snapshot Shop có `stock` (kho dư) và `time_left_ticks`.
- **Dòng `end`** có thêm `days_completed`.
- **Inputs:** thêm `pause`, `shop_done`, `attack`, `photo` (bool, chỉ xét cạnh lên) và `buy` (chuỗi, chỉ chạy tại frame khai báo).
- **Event mới:** `paused`/`resumed` `{}`, `bought{upgrade,level,price,money}`, `buy_failed{action,reason}`.
- **Pause:** khi dừng, `state: "paused"`; `sim_tick`, `phase_tick` và mọi timer đứng yên, chỉ `tick` tăng.
- **Scenario `day`:** gồm `gather` (v1.2: `hold` là mảng cá thể), `quan` (mẫu cho mỗi Ngày; cấm `quan.stock`, `quan.reputation`) và `day{money,earned,reputation,upgrades,day_plan}`.

## 4. Giả định đã chốt
Các chỗ PRD mơ hồ (giá/boa `null` trước khi chốt, họ id khách `C`, luồng RNG `customer_dish`, làm tròn uy tín 6 chữ số, `paid` không kèm `customer_left`…) ghi ở [`docs/clarify.md`](../clarify.md) mục 1–6.

## 5. Lịch sử thay đổi
| Ngày | Đổi gì | Lý do | Ai duyệt |
|---|---|---|---|
| 2026-11-21 | Viết đầy đủ hợp đồng v1.0 từ PRD-0 và code ở tag `phase-1`. Hành vi không đổi. | AC-P1-13 còn thiếu | (cả nhóm xác nhận) |
| 2026-11-21 | v1.1 (Phase 2): số chuẩn, 3 loài cá, Cá Sấu, 2 bếp/4 bàn/6 món, `day_plan`, `shop`, `day`/Shop/pause. | TICKET-02 | Duc1306, congvt |
| 2026-11-21 | **v1.2 (Phase 3, breaking)**: kho đếm → kho cá thể `{id,kind,fresh}`, `tuning.freshness`, event `spoiled`, giữ chỗ theo id, giá theo tươi, `lost`/`items` là cá thể. | TICKET-03, [ADR-0001](../adr/0001-kho-ca-the-v12.md) | Duc1306 (+ TADIZB) |
| 2026-11-21 | Thêm mục 3b: `day`, Shop, pause theo Test Contract v1.1. | TICKET-02 | (cả nhóm xác nhận) |
| 2026-11-21 | Mục 3b: ghi snapshot đổi pha và cách cấp id xuyên Ngày cho khớp code `runner.py` / `sim/day.py`. Hành vi không đổi. | Đối chiếu sau merge | Shirou191 |
| 2026-11-21 | Mở rộng **Cháy món** (`extensions: ["burn"]`, `burn_s: 20`, event `dish_burnt`). Không đổi schema kho, không đổi luật lõi khi `burn_s` null. | Nhóm lên 5 người: TICKET-02/03 yêu cầu ≥ 1 mục mở rộng | hadatttt |
| 2026-11-21 | v1.3 (Phase 4): thêm `bench_cmd`, `soak_cmd` ở gốc manifest. Gameplay/tuning/kho/JSONL giữ nguyên v1.2. | TICKET-04 | Duc1306 (+ TADIZB) |
