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

## Bắt đầu nhanh

```bash
git clone <fork-của-nhóm> && cd <fork-của-nhóm>
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v        # smoke test
python3 -m chonoi.ngay_dem                                          # chơi trọn vòng ngày (5 Ngày) trên trình duyệt
```

Chơi riêng một buổi: `python3 -m chonoi.live --mode gather|quan`. Lưu ý: chạy riêng thì quán **không** có đồ của buổi sáng (kho rỗng) trừ khi truyền `--inventory <file>` do gather ghi bằng `--inventory-out <file>`.

Windows: thêm `PYTHONIOENCODING=utf-8` trước lệnh live. Nếu máy chỉ có `python` thì cần một lệnh `python3` trên PATH, vì `headless_cmd` của test gọi `python3`.

## Điều khiển

| Phím | Buổi sáng (gather, lặn) | Buổi tối (quán) |
|---|---|---|
| **W A S D** / mũi tên | Bơi trái/phải, lặn xuống (S) / nổi lên (W) | Đi trên nhà bè |
| **E** | Hái bông ở nút trên mặt nước; vào bến để **cập bến** (kết thúc buổi, ghi kho) | Nấu ở bếp (lấy đơn cũ nhất), bưng món từ bếp, phục vụ đúng bàn |
| **Space** | Bắt cá khi đang lặn (có hồi chiêu) | — |
| **R** | Chơi lại từ đầu (cùng seed) | như bên trái |
| **H** | Bật/tắt nhật ký sự kiện | như bên trái |

Mẹo: dưới nước tốn oxy. Hết oxy thì bị ngạt và mất Máu, hết Máu thì ngất và kho rỗng. Giỏ có sức chứa giới hạn, đầy thì không hái hay bắt thêm được.

## Cách tính điểm

```
score = earned + 100 × floor(reputation)
```

- `earned`: tổng tiền thu cả lượt, gồm tiền món (giá theo `tuning.menu`) và boa. Boa = `floor(giá × tip_rate)` nếu lúc phục vụ khách còn đủ kiên nhẫn (`tip_min_patience_ratio`), ngược lại boa 0.
- `reputation`: bắt đầu từ 3.0 (`reputation_initial`). Cộng 0.2 (`tip_reputation`) mỗi lần khách trả tiền có boa. Trừ 0.5 (`left_reputation_delta`) mỗi khách hết kiên nhẫn bỏ về; khách rời lúc hết ca thì không bị trừ. Luôn kẹp trong [0, 5].
- Hệ số 100 lấy từ `tuning.score.reputation_multiplier` trong [`game.contract.json`](game.contract.json). Buổi sáng chưa có tiền nên điểm chỉ đến từ uy tín.
- Ví dụ: `earned = 72`, `reputation = 3.2` → `72 + 100 × 3 = 372`.

## Test

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v                                       # toàn bộ test (1 lệnh)
python3 tools/kiem_tat_dinh.py --mode gather --seed 1 --ticks 600 --inputs docs/proof/phase-1/g/day-inputs.json   # kiểm tất định
git config core.hooksPath .githooks                                                              # bật hook test trước khi push
```

Hợp đồng kho, snapshot cho UI và danh sách sự kiện: [`docs/contracts/README.md`](docs/contracts/README.md).

Game cần chế độ **headless** theo Test Contract (`python3 -m chonoi.headless --mode gather|quan …`) để được chạy và chấm tự động. **Công nghệ không ràng buộc**: khung Python trong `chonoi/` chỉ là gợi ý, chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

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
- **HUD bảng gỗ** cho cả hai buổi: thời gian, oxy, Máu, giỏ (sáng); tiền, uy tín, điểm, **kho khả dụng** (tồn − phần khách giữ), món trên tay, gợi ý phím (tối). Phím **H** bật nhật ký sự kiện.
- **Chơi trọn vòng ngày:** `python3 -m chonoi.ngay_dem` chạy CHÍNH `--mode day` của luật (`chonoi/sim/day.py`) trên trình duyệt: menu chính, intro đầu Ngày (Má Tư dặn món + nguyên liệu), HUD "Má Tư cần đã lấy/cần", Cá Sấu + cảnh báo "Thủy quái!", intro buổi tối (nhập kho, món nấu được), kết quả Ngày, Shop (phím 1/2 mua, E đóng), pause P/Esc, tổng kết sau Ngày cuối. Menu/intro dừng đồng hồ bằng nút `pause` của luật. Test: `tests/test_ngay_dem.py`, `tests/test_rules_p2_day.py`.

**Bằng chứng lõi vẫn đúng:** `PYTHONPATH=tests:. python3 -m unittest discover -s tests` → 140 test OK; smoke hộp đen ở Test Contract (gather `dock.json` → quán) cho `stock {"bong_sung":2,"ca_loc":1}` ở tick 0, khớp `gather_end.inventory`; `git diff main -- chonoi/sim chonoi/headless.py chonoi/live.py game.contract.json` trống. Ảnh: `docs/proof/art-*.png`.

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
