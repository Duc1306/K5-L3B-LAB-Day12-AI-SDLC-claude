# Ma trận truy vết Phase 3 (TICKET-03 "Mùa Nước Nổi", Test Contract v1.2)

Kiểm chứng chạy trên `main` ngày 2026-11-21 (Windows 11, Python 3). Commit bàn giao là commit chứa file này. Nhóm chưa có danh sách `AC-P3-xx` riêng, nên các AC dưới đây lập theo TICKET-03: lõi mục 1, Contract v1.2 và DoD.

Bằng chứng chính:
- [`unittest.txt`](../proof/phase-3/unittest.txt): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`. **161 test OK**, gồm 140 test cũ P1–P2 chạy lại và 21 test mới trong `tests/test_rules_p3_fresh.py`.
- [`checks.md`](../proof/phase-3/checks.md): 7 kiểm tra chạy thật bằng `python3 tools/proof_phase3.py`; file vào/ra nằm cùng thư mục.
- Ảnh HUD: [`hud-gather.png`](../proof/phase-3/hud/hud-gather.png), [`hud-quan.png`](../proof/phase-3/hud/hud-quan.png); fixture dùng để chụp nằm cùng thư mục.
- Quyết định đổi schema, bảng tác động và thứ tự tích hợp: [ADR-0001](../adr/0001-kho-ca-the-v12.md). Breaking change và cách chuyển fixture: [CHANGELOG.md](../../CHANGELOG.md).

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-01 `contract_version:"1.2"`, `freshness {100, 0.5, 0.25, 30}` | `test_rules_p3_fresh.Contract` | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-02 Schema kho cá thể: chỉ khóa `items`, mảng `{id,kind,fresh}`, kho rỗng `[]`; file kho đếm, id trùng, kind lạ, `fresh` ngoài miền thì mã 2 và không ghi đầu ra | Chạy thật 4 file sai; `test_smoke_p1.test_inv_bad_schema_exit_2`, `Fixtures.test_fixture_sai_ma_2` | [checks.md #4](../proof/phase-3/checks.md) | Đạt |
| AC-P3-03 Ngưỡng 30: scenario mẫu trong đề phát `spoiled` ở tick 1 đúng nguyên văn; phát một lần; nhiều cá thể thì theo id; kẹp 0 | Chạy thật + `GatherFreshness` | [checks.md #1](../proof/phase-3/checks.md), `threshold.jsonl` | Đạt |
| AC-P3-04 Hao tươi: giỏ 0.5/s, kho quán 0.25/s (kể cả hàng đang giữ); hàng mới là 100 và hao từ bước sau; pause dừng hao | `test_hang_moi_fresh_100_hao_tu_buoc_sau_id_noi_tiep`, `test_kho_quan_hao_025_moi_giay`, `test_pause_dung_hao_tuoi` | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-05 Id `I<n>` theo thứ tự vào giỏ, tăng xuyên pha và Ngày; LIFO khi mất hàng; hàng ươn vẫn chiếm ô | `GatherFreshness`, `test_rules_p2_gather.Monsters` (`lost` là cá thể theo LIFO), `DayItems` | [unittest.txt](../proof/phase-3/unittest.txt), [checks.md #5](../proof/phase-3/checks.md) | Đạt |
| AC-P3-06 Smoke bàn giao file: `gather --inventory-out` ghi một lần, nguyên tử, sắp theo id, đủ chính xác; `quan --inventory --ticks 0` nhận đúng id, kind, độ tươi; ngất thì ghi kho rỗng | Lệnh nguyên văn trong đề + `Handoff` | [checks.md #2–3](../proof/phase-3/checks.md), `handoff-*.json(l)`, `edge-*.json(l)` | Đạt. Nhánh ngưỡng giữ nguyên qua file: kho ghi đúng `30`, bước quán đầu tiên mới ươn |
| AC-P3-07 Giữ chỗ theo id: tươi nhất rồi hòa theo id; hàng ươn không dùng nấu; phần giữ vừa ươn thì nhả và giữ lại đúng một lần theo `order_tick` rồi id bàn; thiếu thì `unfulfillable`, khách vẫn chờ | `QuanFreshness` (4 ca), `Fixtures.test_thieu_reserved_cap_tuoi_nhat_theo_order_tick` | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-08 Giá theo tươi: tiêu đúng các id đang giữ, `base_price = floor(giá × TB fresh / 100)`, boa tính trên giá đã chốt; `cook_started.items` là cá thể sắp theo kind rồi id | `test_gia_theo_tuoi_va_items_la_ca_the` (canh chua 100 + 40 ra giá 62), `test_boa_tinh_tren_gia_da_chot`, `test_rules_quan.FullShift` | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-09 Scenario v1.2: `hold`/`stock` là cá thể, `reserved` là mảng id; phần giữ phải trỏ tới cá thể có trong kho, chưa ươn, đúng công thức, không dùng chung; sai thì mã 2 | `Fixtures.test_fixture_sai_ma_2` (13 ca) | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-10 `day`: bàn giao trong cùng tick đổi pha, không hao thêm; Ngày kế cấp id mới cho mẫu `hold`; Shop hiện kho dư dạng cá thể và không hao | Chạy thật `day --days 2` + `DayItems` | [checks.md #5](../proof/phase-3/checks.md), `day2.jsonl` | Đạt |
| AC-P3-11 HUD cho thấy độ tươi hoặc hàng ươn | Chụp màn hình bằng Chrome headless: gather (giỏ 5/12, thanh 73 %, nhãn "ươn 1") và quán (kho khả dụng có "giữ N", "ươn 1", thanh 56 %) | [hud-gather.png](../proof/phase-3/hud/hud-gather.png), [hud-quan.png](../proof/phase-3/hud/hud-quan.png) | Đạt. Kiểm cú pháp JS bằng `node --check`. **Chưa chơi trọn một vòng `ngay_dem` bằng tay** sau khi đổi |
| AC-P3-12 Regression P1–P2 còn hiệu lực; test đổi có ghi lý do | 140 test cũ chạy lại; lý do đổi ghi trong test và trong [CHANGELOG](../../CHANGELOG.md) mục "Test đổi vì luật mới" | [unittest.txt](../proof/phase-3/unittest.txt) | Đạt |
| AC-P3-13 Tất định và hiệu năng: một Ngày ≤ 20 s; cùng seed thì giống từng byte; hook `pre-push` xanh | Chạy thật; `bash .githooks/pre-push` | [checks.md #6–7](../proof/phase-3/checks.md) | Đạt: một Ngày mất 0.5–1.2 s; sha256 trùng; hook OK (đã đổi sang kho mẫu v1.2) |
| AC-P3-14 Ghi tác động, quyết định đổi schema, thứ tự tích hợp; CHANGELOG; clarify, nhật ký AI, retro | Đọc `docs/` | [ADR-0001](../adr/0001-kho-ca-the-v12.md), [CHANGELOG.md](../../CHANGELOG.md), `docs/clarify.md` #23–#29, `docs/ai-usage-log.md`, `docs/retro.md` | Đạt |
| AC-P3-15 Các lát tích hợp trong fork chung, có đóng góp từng người | `git log` | Commit Phase 3 | **Một phần**: cả 3 lát Phase 3 do Duc1306 làm (co-author TADIZB). Thành viên khác chưa có commit Phase 3 |
| AC-P3-16 Mở rộng (`current`, `reservations`) | — | — | **Không làm**: `team_size` là 4 nên không bắt buộc; chưa khai `extensions` |
| AC-P3-17 Tag `phase-3` trên `main` trước 2:30 | `git rev-parse phase-3^{commit}` | Ghi trong commit gắn tag | Gắn ở commit chứa file này. Không đối chiếu được với mốc 2:30 của buổi lab |
