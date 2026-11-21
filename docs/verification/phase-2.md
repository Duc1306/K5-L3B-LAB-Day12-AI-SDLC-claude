# Ma trận truy vết Phase 2 (TICKET-02, Test Contract v1.1)

Kiểm chứng chạy trên `main` ngày 2026-11-21 (Windows 11, Python 3), commit ghi ở `docs/proof/phase-2/commit.txt`. Nhóm chưa có danh sách `AC-P2-xx` riêng, nên AC dưới đây lập theo TICKET-02: lõi mục 1–2, Test Contract v1.1 mục 4 và DoD.

Bằng chứng chính:
- [`unittest.txt`](../proof/phase-2/unittest.txt): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`. **140 test OK.**
- [`integration.md`](../proof/phase-2/integration.md): smoke tích hợp `gather --inventory-out` → `quan --inventory` với số chuẩn v1.1, cộng regression smoke của Phase 1.
- [`day-checks.md`](../proof/phase-2/day-checks.md): `day --days 1`, `--days 5`, Shop/nâng cấp, pause, tất định, mã thoát. Đầu vào/ra ở `docs/proof/phase-2/d/`.
- Ảnh chơi trên trình duyệt: `docs/proof/phase-2/ui-*.png`.

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P2-01 `contract_version:"1.1"`, tuning chuẩn, 6 nguyên liệu, 6 món theo dữ liệu | unittest `test_rules_p2_gather.StandardNumbers`, `test_rules_p2_quan.StandardData` (`test_so_chuan_v11`, `test_thuc_don_6_mon`, `test_ke_hoach_D1_D5`, `test_shop_chuan`) | [unittest.txt](../proof/phase-2/unittest.txt) | Đạt |
| AC-P2-02 Cá bơi/sinh: 8 đàn đầu ca, 1.5 m/s, đổi hướng 120·k, phản xạ mép, sinh 360·k, trần 12 | unittest `FishInitialAndSpawn`, `FishSwim` | [unittest.txt](../proof/phase-2/unittest.txt) | Đạt |
| AC-P2-03 Cá Sấu patrol/chase/recoil, hit −1 Máu, rơi LIFO `floor(n/2)`, bất tử 90, ngất do quái | unittest `Monsters`, `MonsterFixtures`; chơi thật (ảnh Cá Sấu cắn còn 1 Máu, giỏ 4 → 1) | [unittest.txt](../proof/phase-2/unittest.txt), [ui-gather-ca-sau.png](../proof/phase-2/ui-gather-ca-sau.png) | Đạt |
| AC-P2-04 Quán 2 bếp / 4 bàn / 6 món, lịch khách 120 + 900·k | unittest `TwoStovesFourTables`, `PlanFilter` | [unittest.txt](../proof/phase-2/unittest.txt), [ui-quan-2bep-4ban.png](../proof/phase-2/ui-quan-2bep-4ban.png) | Đạt |
| AC-P2-05 Smoke tích hợp `gather --inventory-out` → `quan --inventory` (đề: phút 20) | Chạy headless thật, so kho với `gather_end` và snapshot quán ở tick 0 | [integration.md](../proof/phase-2/integration.md), `integration-*.json(l)` | Đạt: kho `{bong_sung:2, ca_keo:2, ca_loc:1, keo_neo:1}` khớp ở cả 3 nơi; quán có B1–B2, T1–T4 |
| AC-P2-06 `--mode day` công bố đúng kế hoạch D1–D5, đổi pha cùng tick, chốt Ngày khi Shop đóng | `day --days 1` và `--days 5` thật + `test_rules_p2_day.DayFlowTest` | [day-checks.md §1–2](../proof/phase-2/day-checks.md) | Đạt: thứ tự `day_start → day_plan → phase_start`; `phase_start` ở tick 0/10800/21600; 1 Ngày = 22200 tick; 5 Ngày khớp `tuning.day_plan`; M2 có từ Ngày 3; `days_complete` |
| AC-P2-07 Shop: trừ `money` giữ `earned`, cấp `oxygen`/`hp` áp dụng từ Ngày kế, `buy_failed` | 2 Ngày có inputs mua thật + `ShopTest` | [day-checks.md §3](../proof/phase-2/day-checks.md) | Đạt: Ngày 2 có oxy 2700 tick, 4 Máu; `buy_failed` funds/unknown/max_level |
| AC-P2-08 Pause ở mọi mode: chỉ tăng tick ngoài, `sim_tick`/`phase_tick`/timer đứng yên, `paused`/`resumed`, `state:"paused"` | Thật trong `day` + `PauseTest` (gather, Shop) | [day-checks.md §4](../proof/phase-2/day-checks.md) | Đạt |
| AC-P2-09 Headless một Ngày ≤ 20 s; tất định từng byte | Đo thời gian; chạy 2 lần cùng seed ở cả 3 mode | [day-checks.md §1, §5](../proof/phase-2/day-checks.md) | Đạt: 1.17 s/Ngày, 5 Ngày 3.54 s; sha256 trùng ở gather/quan/day |
| AC-P2-10 CLI/scenario v1.1: `--days` 1..5 chỉ với day, cấm kho file với day, cấm `quan.stock`/`quan.reputation`, `0 ≤ money ≤ earned` | Thật + `DayCliAndScenarioTest` | [day-checks.md §6](../proof/phase-2/day-checks.md) | Đạt (mã 2) |
| AC-P2-11 Chơi trọn vòng ngày với menu, pause và HUD (DayIntro, EveningIntro, DayResult, Shop, Summary; HUD cần lấy, Thủy quái!, Hết hơi!) | `python3 -m chonoi.ngay_dem` chơi thật + `tests/test_ngay_dem.py` (qua HTTP) | `docs/proof/phase-2/ui-*.png` | **Một phần**: chạy được và có test. Intro buổi tối, kết quả Ngày, pause, tổng kết mới kiểm bằng trang dữ liệu giả (khó canh giờ chụp trên máy chủ). **Chưa đo FPS ≥ 30 ở 1280×720.** |
| AC-P2-12 Regression P1 còn hiệu lực với số chuẩn; test đổi có ghi lý do | Lệnh smoke nguyên văn PRD-0; toàn bộ test P1 | [integration.md](../proof/phase-2/integration.md), [unittest.txt](../proof/phase-2/unittest.txt) | Đạt. Test đổi vì luật mới: `test_python_starter_units`, `test_smoke_p1` (`attack` và `--mode day` không còn là mã 2; lý do ghi trong test và commit `e7f27d7`); Duc1306 ghi lý do đổi test quán ở commit `e1dd747` |
| AC-P2-13 Làm rõ, nhật ký AI, retro đã cập nhật | Đọc `docs/` | `docs/clarify.md` #9–#22, `docs/ai-usage-log.md`, `docs/retro.md` | Đạt (retro mới có ghi chép của congvt, cần cả nhóm bổ sung) |
| AC-P2-14 Công việc các lát tích hợp trong fork chung, có đóng góp từng người | `git shortlog -sn phase-1..HEAD` | [commits-by-author.txt](../proof/phase-2/commits-by-author.txt) | **Một phần**: congvt 6, Duc1306 3, Shirou191 1 (+ co-author hadatttt); `TEAM.md` vẫn chưa điền nên commit có thể không được tính |
| AC-P2-15 Tag `phase-2` trên `main` trước 1:55 | `git rev-parse phase-2^{commit}` | Ghi trong commit gắn tag | Gắn ở commit chứa file này. Không đối chiếu được với mốc 1:55 của buổi lab |

## Đánh giá ngắn
- **Đạt:** toàn bộ lõi headless của TICKET-02 (AC-01 → 10, 12). Cả 4 lát đã tích hợp trên `main`: lát 1–3 của Duc1306, lát 4 (`day`/Shop/pause/UI) của congvt.
- **Một phần:**
  - UI chưa đo FPS; 4 màn mới kiểm bằng dữ liệu giả (AC-11).
  - `TEAM.md` chưa điền (AC-14).
- **Rủi ro với test ẩn:** các giả định ở `docs/clarify.md` #17–#22. Hai giả định đáng chú ý nhất:
  - có ghi thêm snapshot ở tick đổi pha;
  - id cá/khách đánh lại từ F1/C1 mỗi Ngày.

  Cần PO hỏi Anh Năm.
- **Cho Phase 3:**
  - Điền `TEAM.md` ngay.
  - Đo FPS trên máy demo.
  - Đọc TICKET-03 (`docs/plan/cho-noi-lab-phase-3.md`) và chia lát trước khi code.
