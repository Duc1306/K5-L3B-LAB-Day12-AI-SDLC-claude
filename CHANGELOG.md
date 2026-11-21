# Changelog

## Unreleased

## [v1.0.0] / [phase-4] — contract v1.3 "Phát hành" (TICKET-04)

### Thêm
- `contract_version:"1.3"`. Gốc manifest khai `bench_cmd: python3 -m chonoi.bench` và `soak_cmd: python3 -m chonoi.soak`. Gameplay, tuning, kho và JSONL **giữ nguyên v1.2**.
- **Benchmark có render** (`chonoi/bench.py`):
  - Cảnh buổi sáng lõi seed 42, Út Sen đứng yên ở bến, 1280×720.
  - Chạy Chromium/Chrome/Edge không giao diện, làm nóng 3 s rồi đo `--duration` giây.
  - Ghi `bench.json` 5 trường `avg_fps, p1_low_fps, frames, measured_s, load_ms`.
- **Soak headless** (`chonoi/soak.py`):
  - Chạy N Ngày trong một tiến trình bằng bot tất định. Kế hoạch D1–D5 lặp ở Ngày 6–10.
  - `soak.json` gồm `days, days_completed, crashes, results[{day, earned, reputation, score}], duration_s`.
- **Cảnh báo dễ nhận biết:** "Thủy quái gần!", "Oxy sắp hết! / Hết hơi!", "Khách sắp giận! Bàn …", mỗi cảnh báo có biểu tượng vẽ bằng canvas. Trên đầu khách có nhãn "Sắp giận".
- **Chế độ tương phản cao:** phím **C** hoặc `?tuong_phan=1`, nhớ trong trình duyệt. Cảnh báo thành hộp đen viền vàng chữ trắng, viền màn hình tím khi có thủy quái, chữ HUD viền đen dày, canvas tăng tương phản.
- README: yêu cầu môi trường, 3 lệnh chạy từ clone sạch, điều khiển, test, headless, bench, soak, giới hạn đã biết. Release notes ở `docs/release/v1.0.0.md`. Bản đóng gói `cho-noi-v1.0.0.zip` đính kèm Release.

### Đổi
- `DaySim`: kế hoạch Ngày n > 5 lấy D((n−1) mod 5 + 1), phục vụ soak. Headless `--days` vẫn giới hạn 1..5 như v1.1.
- Hiệu năng HUD/cảnh lặn, hình vẽ không đổi:
  - Bảng gỗ HUD (`shadowBlur`) vẽ một lần vào canvas phụ rồi `drawImage`.
  - Gân lá dừa nước và lá chét điên điển gộp thành một path cho mỗi màu.

### Test
- Thêm `tests/test_p4_release.py` (9 ca): manifest v1.3, soak (cấu trúc, tất định, tham số sai, chu kỳ kế hoạch), công thức bench, chuỗi cảnh báo.
- Đổi vì luật mới: `test_rules_p2_gather`, `test_rules_p3_fresh` nhận `contract_version` 1.3 (gameplay vẫn v1.2).

 "Mùa Nước Nổi" (TICKET-03)

### Mở rộng Cháy món (`burn`, hadatttt)
- Manifest khai `"extensions": ["burn"]` và `tuning.quan.burn_s: 20`. `chonoi/contract.py` kiểm hai chỗ khớp nhau, từ chối mã mở rộng chưa làm.
- Món chín để quá 1200 tick (20 s) trên bếp thì cháy: bỏ món, bếp rảnh ngay, giữ lại nguyên liệu cho đơn (`reserved`) hoặc `unfulfillable` nếu thiếu. Event `dish_burnt {stove_id, order_id, dish_id, order_status}`. Đúng 1200 tick vẫn bưng được.
- UI: khói, chữ "cháy món!" ở bếp và thoại của Út Sen khi có `dish_burnt`.
- `tests/test_ext_burn.py` (11 test), bằng chứng ở `docs/proof/ext-burn/`.

### Nhóm
- `TEAM.md`: nhóm 5 người; `team: "claude"`, `team_size: 5`.

## [phase-3] — contract v1.2 "Mùa Nước Nổi" (TICKET-03)

### BREAKING
- **Kho đếm → kho cá thể.** File kho, `gather_end.data.inventory`, snapshot `hold` (gather) và `stock` (quán, Shop) giờ là mảng `{id, kind, fresh}`:
  `{"items":[{"id":"I1","kind":"ca_linh","fresh":100}]}`. Kho rỗng là `{"items":[]}`.
  Contract v1.2 trả **mã 2** cho file kho đếm cũ `{"items":{"ca_loc":1}}`, id trùng, kind lạ, `fresh` ngoài [0, 100] hoặc thiếu trường.
- `contract_version` chuyển thành `"1.2"`. Thêm `tuning.freshness {initial:100, gather_decay_per_s:0.5, quan_decay_per_s:0.25, spoiled_below:30}`.
- `customers[].reserved` là **mảng id cá thể**, không còn là map `{kind: n}`.
- `cook_started.data.items`, cùng `lost` trong `monster_hit`/`faint`, là mảng cá thể. `items` sắp theo kind rồi id; `lost` theo thứ tự LIFO.
- **Giá theo tươi:** `base_price = floor(giá niêm yết × trung bình fresh / 100)`, chốt lúc bắt đầu nấu. Boa tính trên giá đã chốt.

### Thêm
- Độ tươi của từng cá thể:
  - Mới lấy là 100, hao từ bước sau: giỏ −0.5/s, kho quán −0.25/s.
  - Dưới 30 là ươn: vẫn chiếm ô nhưng không nấu được.
  - Event `spoiled {item_id, kind, location}` phát đúng một lần, theo id.
  - Pause, món chín và hàng ở Shop không hao.
- Giữ chỗ chọn cá thể tươi nhất, hòa theo id. Phần giữ vừa ươn thì nhả toàn bộ và giữ lại đúng một lần; không đủ thì đơn thành `unfulfillable`.
- Id `I<n>` tăng liên tục qua pha và Ngày. Trong `day`, từ Ngày 2 các cá thể của mẫu `gather.hold` được cấp id mới.
- HUD hiện thanh % tươi theo loại và nhãn đỏ "ươn N". Kho khả dụng ở quán tính theo id.
- `tools/proof_phase3.py`, `docs/proof/phase-3/`, `docs/verification/phase-3.md`, ADR-0001.

### Cập nhật fixture (cách chuyển)
- `gather.hold`: từ `["ca_loc","bong_sung"]` sang `[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":100}]`.
- `quan.stock`: từ `{"ca_loc":2}` sang `[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"ca_loc","fresh":100}]`.
- `customers[].reserved`: từ `{"ca_loc":1}` sang `["I1"]`, hoặc bỏ đi để sim tự cấp (tươi nhất, theo `order_tick` rồi id bàn).
- Trong test có helper `tests/helpers.py`: `items()`, `stock_items()`, `as_items()`, `counts()`, `kinds_of()`.
- File kho mẫu `docs/contracts/inventory.sample.json` đã ở dạng v1.2. Hook `pre-push` dùng file này.

### Test đổi vì luật mới (không phải để cho xanh)
- `test_rules_quan`: giá niêm yết 60 thành giá theo tươi (`price_at`: nấu ở tick 1 thì 59, tổng thu 70 thay cho 72); `reserved` thành mảng id.
- `test_rules_gather`, `test_rules_p2_gather`: `lost`/kho là cá thể; so theo kind/id thay cho mảng chuỗi.
- `test_smoke_p1`:
  - Kho bàn giao so id/kind chính xác và `fresh` với dung sai ±0.01, vì JSONL làm tròn 3 chữ số.
  - Thêm ca mã 2 của v1.2.
- `test_rules_p2_day`, `test_ngay_dem`, `test_python_starter_units`: chỉ đổi fixture sang cá thể.

## [phase-2] — contract v1.1 (TICKET-02)
- Số chuẩn, cá bơi/sinh, Cá Sấu, 2 bếp/4 bàn/6 món, kế hoạch D1–D5, `--mode day`, Shop, pause, HUD vòng ngày.

## [phase-1] — contract v1.0 (PRD-0)
- Gather (oxy, ngạt, hái, bắt cá), quán (khách, bếp, phục vụ, uy tín), file kho đếm.
