# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Bắt đầu nhanh (bản phát hành v1.0.0)

**Yêu cầu môi trường:** Python ≥ 3.8 (đã thử 3.12), chỉ dùng thư viện chuẩn, không cần `pip install`. Một trình duyệt hiện đại để chơi. Lệnh benchmark cần Chromium/Chrome/Edge. macOS, Linux, Windows đều chạy được.

Từ clone sạch, **3 lệnh** là chơi được trọn vòng ngày trên trình duyệt (macOS/Linux):

```bash
git clone https://github.com/Duc1306/K5-L3B-LAB-Day12-AI-SDLC-claude.git
cd K5-L3B-LAB-Day12-AI-SDLC-claude
python3 -m chonoi.ngay_dem        # mở địa chỉ in ra (mặc định http://127.0.0.1:8000/), 5 Ngày
```

Bản đóng gói `cho-noi-v1.0.0.zip` ở GitHub Release `v1.0.0`: giải nén, `cd cho-noi-v1.0.0`, rồi `python3 -m chonoi.ngay_dem`.

Tùy chọn: `--port 0` (cổng ngẫu nhiên), `--so-ngay 1..5`, `--seed N`. Chơi riêng một buổi: `python3 -m chonoi.live --mode gather|quan`. Chạy riêng thì quán **không** có đồ của buổi sáng (kho rỗng), trừ khi truyền `--inventory <file>` do gather ghi bằng `--inventory-out <file>`.

Windows: thêm `PYTHONIOENCODING=utf-8` trước lệnh live. Nếu máy chỉ có `python` thì cần một lệnh `python3` trên PATH, vì `headless_cmd` của test gọi `python3`.

## Điều khiển

| Phím | Buổi sáng (gather, lặn) | Buổi tối (quán) | Shop / menu |
|---|---|---|---|
| **W A S D** / mũi tên | Bơi trái/phải, lặn xuống (S) / nổi lên (W) | Đi trên nhà bè | — |
| **E** | Hái bông ở nút trên mặt nước; vào bến để **cập bến** (kết thúc buổi, ghi kho) | Nấu ở bếp (lấy đơn cũ nhất), bưng món, phục vụ đúng bàn | Đóng Shop |
| **Space** | Bắt cá khi đang lặn (có hồi chiêu) | — | Enter/Space: vào chơi từ menu |
| **1 / 2** | — | — | Mua Bình oxy / Áo phao |
| **P / Esc** | Tạm dừng (dừng đồng hồ và mọi timer, kể cả độ tươi) | như bên trái | như bên trái |
| **C** | **Bật/tắt chế độ tương phản cao** (nhớ giữa các lần mở; hoặc thêm `?tuong_phan=1` vào địa chỉ) | như bên trái | như bên trái |
| **R** / **H** | Chơi lại (cùng seed) / nhật ký sự kiện | như bên trái | — |

**Cảnh báo dễ nhận biết** (chữ + biểu tượng; ở tương phản cao là hộp đen viền vàng, chữ trắng to):
- "Thủy quái gần!" (tam giác "!") kèm viền tím màn hình.
- "Oxy sắp hết! Nổi lên" (bong bóng O₂) khi oxy dưới 25 %; "Hết hơi!" khi oxy cạn.
- "Khách sắp giận! Bàn …" (mặt giận) khi khách chờ còn dưới 25 % kiên nhẫn; trên đầu khách có nhãn "Sắp giận".

Ảnh: `docs/proof/phase-4/canh-bao/`.

Mẹo:
- Dưới nước tốn oxy; hết oxy thì ngạt và mất Máu, hết Máu thì ngất và kho rỗng.
- Hàng hao tươi: ở giỏ 0.5/s, ở kho quán 0.25/s. Dưới 30 là **ươn**, không nấu được. Giá món tính theo độ tươi.

## Cách tính điểm

```
score = earned + 100 × floor(reputation)
```

- `earned`: tổng tiền thu cả lượt, gồm tiền món (giá theo `tuning.menu`) và boa. Boa = `floor(giá × tip_rate)` nếu lúc phục vụ khách còn đủ kiên nhẫn (`tip_min_patience_ratio`), ngược lại boa 0.
- `reputation`: bắt đầu từ 3.0 (`reputation_initial`). Cộng 0.2 (`tip_reputation`) mỗi lần khách trả tiền có boa. Trừ 0.5 (`left_reputation_delta`) mỗi khách hết kiên nhẫn bỏ về; khách rời lúc hết ca thì không bị trừ. Luôn kẹp trong [0, 5].
- Hệ số 100 lấy từ `tuning.score.reputation_multiplier` trong [`game.contract.json`](game.contract.json). Buổi sáng chưa có tiền nên điểm chỉ đến từ uy tín.
- Ví dụ: `earned = 72`, `reputation = 3.2` → `72 + 100 × 3 = 372`.

## Test, headless, benchmark, soak

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v                       # toàn bộ test (200 test, ~50 s)
python3 -m chonoi.headless --mode gather|quan|day --seed 1 --ticks 600 --out out.jsonl   # headless theo Test Contract
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json                  # benchmark có render (cần Chromium/Chrome/Edge)
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json                         # soak 10 Ngày headless bằng bot tất định
python3 tools/kiem_tat_dinh.py --mode quan --seed 3 --ticks 3000 --inventory docs/contracts/inventory.sample.json   # kiểm tất định
git config core.hooksPath .githooks                                               # bật hook test + tất định trước khi push
```

- **Contract v1.3** khai ở gốc [`game.contract.json`](game.contract.json): `headless_cmd`, `bench_cmd`, `soak_cmd`. Gameplay, tuning, kho và JSONL theo v1.2.
- Hợp đồng kho (kho cá thể `{id, kind, fresh}`), snapshot cho UI và danh sách sự kiện ở [`docs/contracts/README.md`](docs/contracts/README.md).
- **Bench** (`chonoi/bench.py`):
  - Dựng máy chủ buổi sáng lõi seed 42, Út Sen đứng yên ở bến.
  - Mở trình duyệt không giao diện 1280×720 (`--headed` để mở cửa sổ thật; `--browser` hoặc biến `CHONOI_BROWSER` để chỉ trình duyệt).
  - Làm nóng 3 s, đo `--duration` giây, ghi `{avg_fps, p1_low_fps, frames, measured_s, load_ms}`.
- **Soak** (`chonoi/soak.py`):
  - Chạy N Ngày trong một tiến trình bằng chính `--mode day` của luật. Bot đi gather → quán → Shop: hái/bắt theo kế hoạch, nấu, bưng, mua nâng cấp. D1–D5 lặp ở Ngày 6–10.
  - Ghi `{days, days_completed, crashes, results[], duration_s}`. Mã 0 khi đạt.

Game cần chế độ **headless** theo Test Contract để được chạy và chấm tự động. **Công nghệ không ràng buộc**: khung Python trong `chonoi/` chỉ là gợi ý, chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

## Giới hạn đã biết (v1.0.0)

- **Hiệu năng cảnh lặn chưa đạt mốc 60 FPS.** Máy đo của nhóm (Windows 11, Chrome headless, vẽ bằng phần mềm) cho `avg_fps 36.9`, `p1_low_fps 21.4`, `load_ms 1432` ([bench.json](docs/proof/phase-4/bench.json)). Các lần đo khác dao động `avg` 23–42 FPS tùy tải máy; load luôn ≤ 2.2 s.
  - Đồ họa thủ tục của cây hái, nền sông và tiền cảnh vẽ khoảng 1.500 path mỗi khung.
  - Bản v1.0.0 đã cache bảng gỗ HUD và gộp path lá/gân lá (20 → ~30 FPS trước khi bỏ công cụ profile).
  - Còn có thể cache lớp nền và cây theo pha.
- Bench cần trình duyệt nhân Chromium. Không tìm thấy thì lệnh báo mã 1 kèm hướng dẫn, không ghi số giả.
- Mở rộng đã làm: **Cháy món** (`burn`, xem mục "Mở rộng đã làm"). Chưa làm các mở rộng còn lại (Lao xua, Vợt, Rắn, Chợ, Sổ tay, Dòng nước lũ, Khách đặt trước, Bảng xếp hạng, Phụ đề SFX). Game chưa có âm thanh.
- Chế độ tương phản cao tăng tương phản và viền chữ HUD/cảnh báo; tranh nền vẫn giữ màu gốc (chỉ áp bộ lọc tương phản).

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

## Mở rộng đã làm

Nhóm 5 người nên đề yêu cầu ít nhất 1 mục (TICKET-02 mục 3, TICKET-03 mục 2). Khai trong `game.contract.json`: `"extensions": ["burn"]`.

**Cháy món (`burn`)**, `tuning.quan.burn_s: 20`:
- Món chín để trên bếp quá 1200 tick (20 s) thì cháy: bỏ món, nguyên liệu mất, bếp rảnh ngay. Đúng 1200 tick vẫn bưng được.
- Đơn của món được giữ lại nguyên liệu ngay (`reserved`), nếu thiếu thì `unfulfillable` và khách vẫn chờ tới hết kiên nhẫn.
- Event `dish_burnt {stove_id, order_id, dish_id, order_status}`. Trên trình duyệt có khói, chữ "cháy món!" và thoại.
- Test: `PYTHONPATH=tests:. python3 -m unittest test_ext_burn -v` (11 test). Kiểm chứng và bằng chứng: [`docs/verification/ext-burn.md`](docs/verification/ext-burn.md), [`docs/proof/ext-burn/`](docs/proof/ext-burn/). Hợp đồng: [`docs/contracts/README.md`](docs/contracts/README.md) mục 3.1.

## Sáng tạo của nhóm

Toàn bộ phần dưới đây là **lớp hiển thị trên trình duyệt** (`chonoi/web/index.html`, khối `ART (nhóm)`) và một script chơi thử; chỉ đọc snapshot, **không đổi** `chonoi/sim/*`, headless, `game.contract.json` hay `docs/contracts/`. Hướng dẫn cho agent: skill [`.agents/skills/thiet-ke-do-hoa`](.agents/skills/thiet-ke-do-hoa/SKILL.md).

- **Buổi sáng:** sông phù sa ánh hồng, bờ dừa nước, nhà sàn xa, nhà bè ở bến; camera bám Út Sen (bản đồ nhỏ góc phải); Út Sen áo bà ba, khăn rằn ca rô, kính lặn tự chế, giỏ đeo hông phồng theo đồ hái; cá theo loài (cá linh vẽ thành đàn); bong bóng thở, viền tối khi sắp hết oxy. **Cây hái vẽ bán thực tế theo hình dạng ngoài đời** (`artNode`): bông súng (lá tròn có khe nổi theo sóng, mặt dưới tím đỏ, hoa cánh nhọn hồng tím + nụ, cọng dài xuống đáy), điên điển (bụi thân mảnh giữa nước lũ, lá kép lông chim, chùm hoa vàng rủ), kèo nèo (cọng lá dày, phiến bầu dục gân cong, ngồng hoa 3 cánh vàng kem); vừa hái thì nước bắn và cây mất hoa/còn cọng cụt kèm "mọc lại Ns", mọc lại thì lớn dần. Ảnh: `docs/proof/art-gather-cay-that.png`.
- **Buổi tối:** quán trên nhà bè vẽ góc chéo 3/4 (bếp cà ràng, quầy, bàn ván, lan can tre), đèn dây vàng, khói bếp, ánh sáng đêm; bong bóng gọi món + thanh kiên nhẫn; thoại giọng Nam Bộ theo sự kiện (`customer_arrived`, `served`, `paid`, `customer_left`…).
- **HUD bảng gỗ** cho cả hai buổi: thời gian, oxy, Máu, giỏ (sáng); tiền, uy tín, điểm, **kho khả dụng** (cá thể chưa ươn và chưa bị khách giữ, có thanh % tươi và nhãn "ươn N"), món trên tay, gợi ý phím (tối). Phím **H** bật nhật ký sự kiện.
- **Khả năng tiếp cận (v1.0.0):** ba cảnh báo có chữ + biểu tượng vẽ bằng canvas (không phụ thuộc font emoji), chế độ tương phản cao (phím **C**). Chỉ là lớp hiển thị, không đổi snapshot hay luật.
- **Chơi trọn vòng ngày:** `python3 -m chonoi.ngay_dem` chạy CHÍNH `--mode day` của luật (`chonoi/sim/day.py`) trên trình duyệt: menu chính, intro đầu Ngày (Má Tư dặn món + nguyên liệu), HUD "Má Tư cần đã lấy/cần", Cá Sấu + cảnh báo "Thủy quái!", intro buổi tối (nhập kho, món nấu được), kết quả Ngày, Shop (phím 1/2 mua, E đóng), pause P/Esc, tổng kết sau Ngày cuối. Menu/intro dừng đồng hồ bằng nút `pause` của luật. Test: `tests/test_ngay_dem.py`, `tests/test_rules_p2_day.py`.

**Bằng chứng lõi vẫn đúng (v1.0.0):**
- `PYTHONPATH=tests:. python3 -m unittest discover -s tests` → **200 test OK** ([unittest.txt](docs/proof/phase-4/unittest.txt)).
- Smoke bàn giao kho cá thể v1.2 và ngưỡng ươn: [docs/proof/phase-3/checks.md](docs/proof/phase-3/checks.md).
- Phần sáng tạo chỉ nằm trong `chonoi/web/index.html`. Riêng v1.0.0 có thay đổi về hiệu năng (cache bảng gỗ, gộp path), hình vẽ không đổi.
- Ảnh: `docs/proof/art-*.png`, `docs/proof/phase-4/canh-bao/`.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.
