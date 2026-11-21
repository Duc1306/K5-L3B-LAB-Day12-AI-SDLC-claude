# Ma trận truy vết Phase 1

Kiểm chứng trên commit `bcd004e` = tag `phase-1` (trên `main`), chạy ngày 2026-11-21 trên Windows 11 + Python 3 (xem `docs/proof/phase-1/commit.txt`). AC lập theo PRD-0 (lõi mục 2, Test Contract v1.0, DoD mục 7) vì `docs/plan/phase-1.md` chưa có danh sách AC riêng.

Bằng chứng chính:
- [`unittest.txt`](../proof/phase-1/unittest.txt): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`. **77 test OK.**
- [`headless-checks.md`](../proof/phase-1/headless-checks.md): 7 nhóm kiểm chứng chạy `chonoi.headless` thật. Đầu vào và đầu ra nằm ở `smoke/` và `g/`.
- Ảnh chơi trên trình duyệt: `docs/proof/art-*.png`.

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-01 Gather: bơi, ramp, chặn biên, oxy, ngạt, ngất, 3 Máu | unittest `test_rules_gather` (oxy, `choke` ở t+59, nổi lên đúng bước thì không ngạt, ngất LIFO) + `test_smoke_p1` (`move_01..03`, ramp, mép) | [unittest.txt](../proof/phase-1/unittest.txt) | Đạt |
| AC-P1-02 Gather: hái nút ở mặt nước, `hold_full`, mọc lại | unittest `test_hai_*`, `test_hold_full_khi_hai`, `test_node_regrown_*`, `test_khong_hai_duoi_nuoc` | [unittest.txt](../proof/phase-1/unittest.txt) | Đạt |
| AC-P1-03 Gather: bắt cá khi lặn, hồi chiêu, đàn gần nhất | unittest `test_bat_*`, `test_hoi_chieu_dung_lai_tu_t_cong_L`, `test_hold_full_giu_dan_*` | [unittest.txt](../proof/phase-1/unittest.txt) | Đạt |
| AC-P1-04 Gather kết thúc `docked`/`time`/`fainted`, file kho theo mục G (ngất ghi rỗng, chạm `--ticks` không ghi) | headless checks 1–4 + unittest `test_inv_01_*`, `test_time_ends_gather_and_keeps_hold` | [headless-checks.md §1–4](../proof/phase-1/headless-checks.md) | Đạt |
| AC-P1-05 Quán: khách theo lịch, giữ chỗ nguyên liệu, `no_dish`, hết bàn, kiên nhẫn, bỏ về trừ uy tín | unittest `test_rules_quan` (`test_khach_dau_den_*`, `test_no_dish_*`, `test_het_kien_nhan_*`…) | [unittest.txt](../proof/phase-1/unittest.txt) | Đạt |
| AC-P1-06 Quán: nấu → bưng → phục vụ → trả tiền, boa, hết ca `closing` | unittest `test_nau_bung_phuc_vu_tra_tien`, `test_phuc_vu_boa_*`, `test_het_ca_*` | [unittest.txt](../proof/phase-1/unittest.txt) | Đạt |
| AC-P1-07 Nối 2 tiến trình qua file kho (smoke hộp đen) | Lệnh smoke ở cuối Test Contract; một ngày thật bằng inputs (hái + bắt cá + cập bến → quán đọc kho) | [headless-checks.md §1, §5](../proof/phase-1/headless-checks.md), `smoke/`, `g/day-*` | Đạt: quán ở tick 0 có `stock {"bong_sung":2,"ca_loc":1}`, khớp `gather_end.inventory` |
| AC-P1-08 Headless đúng Test Contract: cờ, mã thoát, JSONL, tất định | unittest `test_smoke_p1` (`con_01..03`, mode sai) + checks 6–7 (sha256 trùng khi chạy lại; tick lặp / kind lạ / cờ sai mode → mã 2) | [headless-checks.md §6–7](../proof/phase-1/headless-checks.md) | Đạt. Mã **1** (lỗi ghi đầu ra) chưa có ca kiểm riêng. |
| AC-P1-09 Điều khiển WASD/E/Space + HUD tối thiểu (sáng: thời gian, oxy, Máu, giỏ; tối: kho khả dụng, món gọi, kiên nhẫn, bếp, trên tay, tiền, uy tín) | Chơi trên `chonoi.live` và chụp màn hình; HUD kho khả dụng so với snapshot (khách giữ 3 cá linh + 1 điên điển → HUD x0, giữ 3/1) | `docs/proof/art-gather-hud-go.png`, `art-quan-kho-kha-dung.png`, `art-quan-3-4-that.png` | Đạt (kiểm bằng mắt) |
| AC-P1-10 `game.contract.json` khớp bản chạy, đủ khóa v1.0 | So `tuning` với preset trong PRD bằng script: không có khác biệt; đủ `build_cmd`/`run_cmd`/`headless_cmd` | Lệnh so sánh ghi trong mục Đánh giá | **Một phần**: tuning khớp preset, nhưng `team` vẫn là `"ten-nhom"` và `team_size` = 4, chưa khớp danh sách thành viên (TEAM.md trống) |
| AC-P1-11 README: chạy từ clone sạch ≤ 3 lệnh (macOS/Linux), điều khiển, cách tính điểm, lệnh test | Đọc README | `README.md` | **Chưa đạt**: có 3 lệnh chạy và lệnh test; **thiếu** điều khiển và công thức điểm (`earned + 100 × floor(reputation)`); chưa thử trên macOS/Linux |
| AC-P1-12 TEAM.md + collaborator + mỗi người ≥ 3 commit có nội dung | `python3 tools/check_team.py`; `git shortlog -sn phase-1` | [check_team.txt](../proof/phase-1/check_team.txt), [commits-by-author.txt](../proof/phase-1/commits-by-author.txt) | **Chưa đạt**: TEAM.md chưa điền (check_team báo 4 thành viên thiếu tên và handle). Commit tới tag: congvt 4, Duc1306 4; các thành viên khác 0 ("Hai Duong" là tác giả starter) |
| AC-P1-13 Hợp đồng kho có schema + ví dụ ở `docs/contracts/` | Đọc thư mục | `docs/contracts/inventory.sample.json`, `docs/contracts/README.md` | **Một phần**: có file mẫu hợp lệ; README hợp đồng vẫn là mẫu, chưa ghi schema, giao diện sim–UI, danh sách sự kiện |
| AC-P1-14 Ghi chép: verification, clarify, ai-usage-log, retro, members | Đọc `docs/` | `docs/clarify.md` (8 mục), file này | **Một phần**: clarify đủ; `ai-usage-log.md` mới có dòng của congvt; `retro.md` và `docs/members/<handle>.md` chưa có nội dung |
| AC-P1-15 Sáng tạo của nhóm không đổi lõi, có bằng chứng | Mục "Sáng tạo của nhóm" trong README; `git diff 533e033 bcd004e -- chonoi/sim chonoi/headless.py chonoi/live.py chonoi/runner.py chonoi/inventory.py game.contract.json docs/contracts tests` trống | `README.md`, unittest | Đạt |
| AC-P1-16 Tag `phase-1` trỏ commit bàn giao trên `main`, trước 1:00 | `git rev-parse phase-1^{commit}` = `bcd004e` = `origin/main` lúc gắn | Tag tạo lúc 2026-11-21 11:33 +0700 | **Một phần**: đúng commit trên `main`; không đối chiếu được với mốc 1:00 của buổi lab, và bằng chứng trong file này được commit **sau** tag |

## Đánh giá ngắn
- **Đạt:** toàn bộ lõi gameplay và Test Contract (AC-01→09, 15). Nối 2 tiến trình qua file kho chạy đúng cả 3 nhánh kết thúc (docked/time/fainted) và tất định từng byte.
- **Chưa đạt / một phần** (phần lớn là ghi chép và thông tin nhóm, không phải code):
  - TEAM.md và `team`/`team_size` (AC-10, 12)
  - README thiếu điều khiển và cách tính điểm (AC-11)
  - Hợp đồng tích hợp chưa viết (AC-13)
  - ai-usage-log, retro, members (AC-14)
  - Mã thoát 1 chưa có ca kiểm (AC-08)
- **Cần chỉnh cho phase sau:**
  - Điền TEAM.md trước mọi thứ, vì commit của người không có trong TEAM.md không được tính.
  - Bổ sung README (điều khiển, điểm).
  - Ghi hợp đồng kho/sự kiện vào `docs/contracts/README.md`.
  - Mỗi người thêm ít nhất 3 commit.
  - Hỏi PO về góc nhìn 3/4 của quán (clarify #8) và chờ đề Phase 2 để làm `--mode day` (clarify #7).
