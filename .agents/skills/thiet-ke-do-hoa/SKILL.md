---
name: thiet-ke-do-hoa
description: Thiết kế và vẽ đồ họa, animation, thoại cho game Chợ Nổi (cảnh lặn gather nhìn ngang, nhà bè/quán nhìn từ trên xuống) trong chonoi/web/index.html. Dùng khi được yêu cầu vẽ lại nhân vật Út Sen, cá, bông, bếp, bàn, khách, cảnh sông/nhà bè, ánh sáng sáng/tối, hiệu ứng, thoại giọng Nam Bộ, hoặc thêm asset ngoài và ghi CREDITS.md.
---

# Skill: Thiết kế đồ họa Chợ Nổi

Mục tiêu: thay hình khối tạm của starter bằng đồ họa mang hồn sông nước miền Tây, animation mượt,
**không** chạm vào luật chơi, headless hay contract.

## 0. Đọc trước khi làm
1. `AGENTS.md` (quy ước nhóm) và README mục "Tự do sáng tạo".
2. `chonoi/web/index.html`: hàm `drawGather`, `drawQuan`, `KIND_COLOR`, `KIND_NAME`, `frame`.
3. `game.contract.json` → `tuning.gather` / `tuning.quan` để biết thực thể nào tồn tại (kind, bounds).
4. `CREDITS.md`.

## 1. Ràng buộc kỹ thuật (bắt buộc)
- **Renderer chỉ đọc snapshot** (`GET /state`) và gửi phím. Không thêm logic luật ở client, không
  suy đoán trạng thái game; trường nào snapshot chưa có thì bỏ qua (`?.`, `?? `).
- **Không sửa** `chonoi/sim/*`, `chonoi/headless.py`, `game.contract.json`, `docs/contracts/` cho mục đích đồ họa.
  Đồ họa không được làm đổi output JSONL headless.
- **Kích thước/vị trí lấy từ `snap.meta`** (bounds, radius…) như starter đang làm, không hard-code số liệu luật.
  Hằng số *thẩm mỹ* (màu, độ dày nét, biên độ nhấp nhô) đặt trong một object `ART` ở đầu khối vẽ.
- `live.py` chỉ phục vụ `index.html`, nên mặc định **vẽ thủ tục bằng Canvas 2D** (path, gradient).
  Ảnh/sprite ngoài: nhúng data URI nhỏ (< ~200 KB tổng). Nếu cần phục vụ file tĩnh thì đó là sửa khung
  giảng viên → phải báo nhóm và ghi lý do trong commit (đừng tự làm).
- Gom code đồ họa vào một khối có rào rõ ràng trong `index.html`:
  `// ===== ART (nhóm) BEGIN =====` … `// ===== ART (nhóm) END =====`, để dễ review và merge.
- Ngẫu nhiên trang trí (sóng, bọt, khói) dùng PRNG riêng có seed trong client (vd. mulberry32),
  không bao giờ ảnh hưởng `Streams` của sim. `Math.random` chỉ được dùng cho hiệu ứng thuần thị giác.
- Giữ lại các lớp "debug" (vòng interact/catch radius) nhưng làm mờ, bật/tắt bằng phím `H` nếu muốn.
- **Tỉ lệ và khung nhìn chỉnh ở một chỗ**: `ART.size` (kích thước người/cá/nhà bè theo đơn vị thế giới,
  Út Sen là thước chuẩn) và `ART.view` (camera gather: `rows` = số đơn vị thấy theo chiều dọc; nhỏ hơn = to hơn).
  Muốn "to hơn" thì phóng camera, **không** phóng riêng một vật làm lệch tỉ lệ. Cảnh xa (bờ, nhà sàn) vẽ theo
  cỡ cố định `fs` để giữ chiều sâu; luôn có bản đồ nhỏ (`artMinimap`) vì camera không thấy cả sông.

## 2. Art bible

### Bảng màu (hex gợi ý — chỉnh được, nhưng giữ tông)
| Vai trò | Sáng sớm (gather) | Tối (quan) |
|---|---|---|
| Trời | gradient `#f7c9b0` → `#ffe6c7` (ánh hồng) | `#141a33` → `#2a2f55` |
| Mặt nước phù sa | `#b9854f` | `#4a3524` phản chiếu đèn |
| Nước sâu | `#8a5a2e` → `#4f321b` | — |
| Dừa nước | `#4f7a3a`, gân `#6f9a4a` | `#24361f` (bóng tối) |
| Gỗ bè / sàn | `#8d6e4b`, ván tối `#6b4a2b` | `#5a4330` |
| Đèn dây vàng | — | lõi `#ffd45a`, quầng `rgba(255,200,90,.25)` |
| Khói bếp | — | `rgba(220,220,220,.35)` tan dần |
| Ánh lửa bếp | — | `#ff8a3d` nhấp nháy |

Nguyên tắc: nước **đục màu phù sa** (nâu vàng), không xanh biển trong vắt. Càng sâu càng tối và giảm
tầm nhìn (lớp phủ alpha tăng theo `d`). Đặt tia nắng xiên mờ gần mặt nước buổi sớm.

### Hai góc nhìn
- **Gather – mặt cắt nhìn ngang**: trục `x` sang phải, `d` xuống. Lớp từ xa đến gần (parallax nhẹ theo
  `player.pos[0]`): trời hồng → bờ dừa nước + nhà sàn xa → ghe/bến (dock) → mặt nước gợn → lòng sông
  bùn, rễ, bèo. Bông điên điển/bông súng mọc ở mặt nước (`d≈0`); cá bơi dưới sâu.
- **Quán – góc nhìn chéo 3/4** (luật vẫn là `[x, z]` nhìn từ trên; chỉ cách *vẽ* là chéo, theo ảnh mẫu nhóm chọn):
  chiếu bằng `qView(...).P(x, z, cao)`; vật sắp theo `z` giảm dần (xa vẽ trước). Sàn ván bè, mặt trước gỗ súc + phao,
  vách gỗ sau bếp, lan can tre (chừa lối ở mặt trước), cột cao treo dây đèn vàng võng. Bếp cà ràng trên bệ gạch
  (miệng lò có lửa + củi), quầy đá phía trước (ống đũa, chồng dĩa); bàn ván dọc + ghế đẩu gỗ, khách ngồi phía sau
  bàn quay mặt ra. Bong bóng gọi món có tên ngắn + hình món + thanh kiên nhẫn xanh→vàng→đỏ.
- **HUD bảng gỗ dùng chung hai buổi**: cột chỉ số trên-trái (`hudStats`), thanh Kho/Giỏ có icon dưới-trái (`hudKho`,
  icon từ `drawKindIcon`), ô Trên tay/Thao tác dưới-phải có gợi ý phím (`hudHand`). Gợi ý chỉ để hiển thị, luật do máy chủ quyết.
  Phím H bật nhật ký sự kiện của starter.
- **Nối ngày → đêm khi chơi thử**: `python tools/choi_ngay_dem.py` (dùng file kho, không phải `--mode day`);
  trình duyệt hiện màn hoàng hôn (`transitionDraw`) khi `snap.mode` đổi gather → quan.

### Nhân vật Út Sen
- Áo bà ba (trắng ngà `#f2ece0` hoặc nâu `#7a4a2a`), quần đen; **khăn rằn ca rô đen‑trắng** quàng cổ
  hoặc buộc đầu; **kính lặn tự chế** (khung ruột xe đen, mắt kính xanh nhạt) — đeo lên mắt khi dưới nước,
  kéo lên trán khi trên bè; **giỏ lưới** đeo hông, phồng dần theo `hold` / số món trong kho.
- Gather (nhìn ngang): tư thế bơi theo `heading_deg`, chân đạp theo chu kỳ, tóc/khăn bay ngược hướng bơi,
  bong bóng thở ra theo nhịp; oxy thấp → bong bóng dồn dập, viền màn hình tối dần.
- Quán (nhìn xuống): vòng đầu + vai + khăn, hướng theo vector di chuyển; khi cầm món (`snap.hand`) vẽ tô/dĩa trên tay.
- Bắt đầu bằng hình khối (ellipse, capsule) đúng tỉ lệ và màu, sau đó mới thêm chi tiết.

### Đối tượng (`kind` → hình)
- `ca_linh`: cá nhỏ thân bạc dẹt, bơi thành đàn lấp lánh. `ca_loc`: thân dài tròn, lưng xám xanh, đốm đen.
- `ca_keo` (nếu có): thân thon nâu vàng, hay sát đáy bùn.
- `bong_dien_dien`: chùm hoa vàng trên cành mảnh. `bong_sung`: cọng dài, hoa tím hồng, lá tròn nổi.
  `keo_neo`: lá xanh dài. Node chưa mọc lại → héo/mờ, mọc lại có hiệu ứng nở.
- Khách: người ngồi ghế đẩu, bong bóng nhỏ hiện món muốn; thanh kiên nhẫn đổi màu xanh → vàng → đỏ.
- Kind lạ: rơi về hình khối + màu từ `KIND_COLOR`, không crash.

## 3. Animation mượt
- Vẽ theo `requestAnimationFrame`; mọi chuyển động trang trí dùng thời gian thực `performance.now()`
  (không đếm frame) để độc lập FPS.
- **Làm mượt vị trí**: dùng `smoothBegin` / `smoothPos(key, pos)` / `smoothAngle(key, rad)` có sẵn trong
  khối ART — vị trí vẽ đuổi theo snapshot theo hàm mũ (`k = 1 - exp(-dt·20)`), chịu được poll không đều.
  Nhảy xa > 3 đơn vị hoặc `tick` giảm (restart) → cắt thẳng. Góc quay theo đường ngắn nhất.
  Key có tiền tố mode (`gather:fish:F1`). Chỉ dùng cho hình; HUD và số liệu vẫn đọc snapshot gốc.
- Hiệu ứng nền: mặt nước gợn (sin nhiều tần số), dừa nước đung đưa, đèn dây lắc, khói bay lên và tan,
  ánh lửa nhấp nháy. Biên độ nhỏ, không gây rối mắt.
- Sự kiện (`snap.events`) → hiệu ứng ngắn 200–600 ms: nhặt bông (lá rung + chữ "+1"), bắt cá (vòng nước
  bắn), bị sặc (bong bóng đỏ + rung nhẹ), giao món (hơi nóng bốc), khách bỏ đi (khói xám). Chỉ phản ứng
  với sự kiện, không tự sinh trạng thái.
- Tôn trọng `matchMedia('(prefers-reduced-motion: reduce)')`: giảm rung lắc/parallax.
- Phong cách: chọn **một** hướng và giữ nhất quán — hoạt hình (nét viền, màu phẳng, squash & stretch)
  hoặc bán thực tế (gradient, ánh sáng, bóng đổ). Ghi lựa chọn vào README mục "Sáng tạo của nhóm".
- Hiệu năng: mục tiêu 60 FPS trên laptop thường; cache nền tĩnh vào `OffscreenCanvas` / canvas phụ,
  chỉ vẽ lại khi đổi kích thước.

## 4. Thoại giọng Nam Bộ
- Chỉ là lớp trình bày ở client (bong bóng thoại, toast); headless không bị ảnh hưởng.
- Ngắn, tự nhiên, ấm áp; dùng từ địa phương vừa phải: *nè, nghen, hông, dữ thần, quá trời, hết sẩy,
  liền, tui, bển, mần*. Ví dụ:
  - Mở buổi sáng: "Nước lớn rồi, Út đi hái bông điên điển nghen!"
  - Bắt cá linh: "Cá linh về quá trời quá đất!"
  - Oxy thấp: "Hổng được, ngộp rồi, trồi lên thở cái đã!"
  - Khách tới: "Dạ, chú ngồi chơi, có liền nè!" · Khách bỏ đi: "Thôi chết, để chú đợi lâu quá…"
- Đặt thoại trong một bảng `LINES` (key = tên sự kiện), chọn câu bằng PRNG trang trí, có cooldown để không spam.
- Không biếm họa giọng nói, không chế giễu nghèo khó, nghề nghiệp hay ngoại hình.

## 5. Tôn trọng văn hóa
- Áo bà ba, khăn rằn, ghe xuồng, nhà bè vẽ đúng hình dạng cơ bản; tham khảo ảnh tư liệu, không bịa chi tiết lố.
- Không dùng biểu tượng tôn giáo/tâm linh (miếu, bàn thờ, nhang) làm vật trang trí hay vật phẩm game.
- Món ăn, cá, bông dùng tên tiếng Việt đúng (lấy từ `KIND_NAME`, có dấu đầy đủ).
- Chỗ chưa chắc (trang phục, phong tục) → ghi `docs/clarify.md`, hỏi PO, không tự quyết.

## 6. Asset ngoài & CREDITS.md
- Ưu tiên tự vẽ bằng code. Asset ngoài chỉ nhận giấy phép **CC0, CC‑BY, CC‑BY‑SA, MIT/OFL** (font), có
  link nguồn. Không lấy ảnh Google/Pinterest, không lấy asset game thương mại, không bắt chước game có sẵn.
- Asset do AI tạo: ghi công cụ, ngày, prompt tóm tắt; nhóm chịu trách nhiệm kiểm tra không giống tác phẩm có bản quyền.
- Mỗi asset thêm một dòng vào `CREDITS.md`:

  ```
  | Asset | Dùng ở | Tác giả / nguồn (URL) | Giấy phép | Chỉnh sửa |
  |---|---|---|---|---|
  | wave-loop.png | gather – mặt nước | Tên tác giả, https://… | CC0 | đổi màu sang phù sa |
  ```
  Công cụ AI (kể cả agent này) ghi ở mục "Công cụ AI" của `CREDITS.md`.

## 7. Quy trình làm một lát đồ họa
1. Chọn **một** lát nhỏ (vd. "nền sông sáng sớm", "Út Sen bơi", "quán ban đêm") — không làm tất cả một lần.
2. Phác hình khối 2D đúng bố cục + màu → chạy thử → thêm chi tiết → thêm animation.
3. Chạy thử: `python3 -m chonoi.live --mode gather` và `--mode quan`; kiểm tra thu/phóng cửa sổ, bấm R
   (restart không bị nội suy giật), không có lỗi trong console.
4. Chứng minh không phá lõi:
   - `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` xanh.
   - `git diff --stat` chỉ chạm `chonoi/web/index.html`, `CREDITS.md`, README/docs.
5. Lưu ảnh chụp màn hình vào `docs/proof/` (vd. `docs/proof/art-gather-dawn.png`), ghi vào README mục
   "Sáng tạo của nhóm" và `docs/ai-usage-log.md`.

## Checklist hoàn thành
- [ ] Chỉ đọc snapshot; không đổi sim/headless/contract.
- [ ] Gather nhìn ngang, nước phù sa, ánh hồng buổi sớm, bờ dừa nước.
- [ ] Quán nhìn từ trên xuống, nhà bè, đèn dây vàng, khói bếp.
- [ ] Út Sen: áo bà ba, khăn rằn, kính lặn tự chế, giỏ lưới.
- [ ] Animation nội suy mượt, độc lập FPS, có reduced‑motion.
- [ ] Thoại Nam Bộ tôn trọng, có cooldown.
- [ ] Mọi asset ngoài có dòng trong `CREDITS.md`; test xanh; có ảnh proof.
