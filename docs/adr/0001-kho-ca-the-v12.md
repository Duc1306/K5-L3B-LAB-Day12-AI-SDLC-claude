# ADR-0001: Kho đếm → kho cá thể có độ tươi (contract v1.2)

- Trạng thái: chấp nhận
- Ngày, người quyết: 2026-11-21 (Phase 3), Duc1306 làm cả 3 vai A/B/C cho lát này (pair TADIZB)

## Bối cảnh
TICKET-03 "Mùa Nước Nổi" là change request **breaking**:
- File kho, `gather.hold`, `quan.stock` và `customers[].reserved` đổi từ đếm theo loại sang cá thể `{id, kind, fresh}`.
- Giữ chỗ chuyển từ theo lượng sang theo id. Giá niêm yết chuyển sang giá theo độ tươi.
- Contract v1.2 phải trả mã 2 cho file kho đếm cũ.

Code v1.1 thì giữ kho dạng `{kind: n}` ở cả gather (`hold` là mảng kind), quán, `day`/Shop và HUD.

## Các lựa chọn đã cân nhắc
1. **Giữ hai schema song song lâu dài**: cờ phiên bản ở mọi chỗ. Phức tạp, dễ lệch, mà đề chỉ cần v1.2.
2. **Đổi thẳng sang v1.2 trong một lát tích hợp, giữ adapter nhỏ**: chọn cách này.
   - Đầu đọc vẫn chọn schema theo `contract_version` (`inventory.uses_item_schema`), nên đọc được kho đếm nếu chạy contract < 1.2.
   - Fixture test cũ chuyển sang v1.2 qua helper (`tests/helpers.py`: `as_items`, `stock_items`, `counts`, `kinds_of`).
3. **Lưu độ tươi bằng số thực**: hao 0.5/60 mỗi tick cộng dồn sai số, có thể lệch nhánh ở ngưỡng 30. Loại.

## Quyết định
- Thêm module `chonoi/sim/fresh.py`:
  - Độ tươi lưu bằng **đơn vị nguyên 1/240 điểm** (gather −2/tick, quán −1/tick). Giá trị không biểu diễn chính xác thì dùng `Fraction`.
  - So ngưỡng trên đơn vị trước khi làm tròn.
  - Ra ngoài thì đổi về `fresh` số thực: JSONL làm tròn 3 chữ số, file kho giữ đủ chính xác.
  - Khi đọc lại, chốt về đơn vị nguyên nếu lệch < 1e-7 đơn vị.
- Id cá thể `I<n>` dùng một `IdAllocator` riêng (`item_ids`), tách khỏi id cá/khách. Trong `day`, `DaySim` giữ một allocator cho mọi Ngày.
- Bật v1.2 cùng lúc ở cả hai đầu bàn giao (gather ghi, quán đọc) trong cùng commit, để `main` không có trạng thái nửa vời.

## Hệ quả — bảng tác động

| Module | File đổi | Test giữ / đổi / thêm | Người phụ trách |
|---|---|---|---|
| Adapter / schema kho | `chonoi/inventory.py` (đọc/ghi v1.2, chọn schema theo version), `chonoi/sim/fresh.py` (mới), `chonoi/headless.py` (truyền `contract_version`), `game.contract.json` (`1.2`, `freshness`), `chonoi/contract.py` (kiểm `freshness`), `docs/contracts/` | Thêm: `test_rules_p3_fresh.Fixtures`, `Contract`; đổi: `test_smoke_p1.test_inv_bad_schema_exit_2` (thêm ca v1.2) | Duc1306 (C) |
| Lặn (gather) | `chonoi/sim/gather.py`: giỏ cá thể, hao đầu bước, `spoiled`, `lost` cá thể, `item_ids` | Thêm: `GatherFreshness`, `Handoff`; đổi: `test_rules_gather` (ngất/kho), `test_rules_p2_gather` (`lost`) | Duc1306 (A) |
| Quán | `chonoi/sim/quan.py`: kho cá thể, hao 0.25/s, giữ theo id, giữ lại khi ươn, giá theo tươi; `chonoi/scenario.py` (`hold`/`stock`/`reserved`) | Thêm: `QuanFreshness`; đổi: `test_rules_quan` (giá 60 → giá theo tươi, `reserved` mảng id), `test_rules_p2_quan` | Duc1306 (B) |
| `day` / Shop | `chonoi/sim/day.py`: `item_ids` xuyên Ngày, Ngày ≥ 2 cấp id mới cho mẫu `hold`, kho dư Shop là mảng | Thêm: `DayItems`; đổi: fixture `test_rules_p2_day`, `test_ngay_dem` | Duc1306 (C) |
| HUD | `chonoi/web/index.html`: đọc cá thể, thanh % tươi, nhãn "ươn N", kho khả dụng theo id | Bằng chứng ảnh `docs/proof/phase-3/hud/` | Duc1306 (C) |
| QA | `.githooks/pre-push` (kho mẫu v1.2), `tools/proof_phase3.py`, `docs/verification/phase-3.md` | Regression P1–P2: 140 test cũ đều chạy lại; test đổi có ghi lý do trong test và CHANGELOG | Duc1306 (C) |

**Thứ tự tích hợp (giữ `main` chạy được):**
1. Schema/adapter + `fresh.py`.
2. Gather.
3. Quán + scenario.
4. `day`.
5. Chuyển fixture test cũ.
6. Test mới.
7. HUD.
8. Bằng chứng + tag.

Bước 1–4 chỉ đẩy lên cùng nhau sau khi toàn bộ test xanh, vì bật v1.2 ở một đầu sẽ làm vỡ đầu kia.
