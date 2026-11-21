# Kiểm chứng mở rộng Cháy món (`burn`)

Người làm: hadatttt. Chạy trên `main` + các commit `feat(ext-burn)` (Windows 11, Python 3.11), ngày 2026-11-21.
Lý do làm: nhóm lên 5 người, TICKET-02 mục 3 và TICKET-03 mục 2 yêu cầu **ít nhất 1 mục mở rộng**
(verification Phase 3, AC-P3-16 ghi "Không làm" khi còn khai 4 người).

Nguồn luật: [TICKET-02 mục 3](../plan/cho-noi-lab-phase-2.md) (bảng Mở rộng), Test Contract v1.1 mục 4.1 (`quan.burn_s` hữu hạn),
4.3 (`ready_ticks` dựng tuổi món chín), 4.4 (`dish_burnt`), 4.5 (xét chín/cháy theo id bếp trước di chuyển/tương tác).

| AC | Cách kiểm | Bằng chứng | Kết quả |
|---|---|---|---|
| EXT-B-01 Khai `extensions: ["burn"]` và `burn_s: 20`; hai chỗ phải khớp, mã lạ/chưa làm → mã 2 | `Manifest` (2 test, 10 ca sai) | [unittest.txt](../proof/ext-burn/unittest.txt) | Đạt |
| EXT-B-02 Đúng 1200 tick vẫn bưng được | `test_dung_1200_tick_van_bung_duoc` | unittest | Đạt |
| EXT-B-03 Quá 1200 tick: bỏ món, bếp idle ngay, giữ lại cho đơn (`reserved`) | `test_qua_1200_tick_thi_chay_va_giu_lai_cho_don` + headless một vòng nấu thật | unittest, [flow-events.txt](../proof/ext-burn/flow-events.txt) | Đạt: chín ở tick 361, cháy ở tick 1562 (= 361 + 1201), đơn giữ lại cá thể `I2` |
| EXT-B-04 Thiếu nguyên liệu → `unfulfillable`, khách chờ tới hết kiên nhẫn | `test_thieu_nguyen_lieu_thi_unfulfillable_khach_van_cho` | unittest | Đạt |
| EXT-B-05 Cháy xét trước tương tác; giữ lại đủ thì nấu lại ngay cùng bước | `test_chay_truoc_tuong_tac_nen_khong_bung_duoc`, `test_chay_roi_nau_lai_ngay_trong_cung_buoc` | unittest | Đạt |
| EXT-B-06 Nhiều bếp cháy cùng bước: xét theo id bếp | `test_hai_bep_xet_theo_id_bep` | unittest | Đạt |
| EXT-B-07 Món trên tay không cháy | `test_mon_tren_tay_khong_chay` | unittest | Đạt |
| EXT-B-08 Event `dish_burnt {stove_id, order_id, dish_id, order_status}` | Các test trên so nguyên `data` | unittest, flow-events.txt | Đạt |
| EXT-B-09 Tất định | `tools/kiem_tat_dinh.py` cùng scenario/inputs, và `quan` seed 7, `day` seed 1 | [tat-dinh.txt](../proof/ext-burn/tat-dinh.txt) | Đạt |
| EXT-B-10 Không làm vỡ lõi và các phase trước | Toàn bộ unittest | unittest.txt: **172 test OK** (161 cũ + 11 mới) | Đạt. Một test chuẩn đổi `burn_s` null → 20 (`test_rules_p2_quan.test_bep_ban_chuan`), có ghi lý do |
| EXT-B-11 UI cho thấy món cháy | Chạy `chonoi.live --mode quan --scenario docs/proof/ext-burn/ui-sc.json`, đợi tick 181 | [ui-chay-mon.jpg](../proof/ext-burn/ui-chay-mon.jpg) | Đạt: chữ đỏ "cháy món!" + khói ở B1, thoại Út Sen, kho hiện "giữ 1" |

**Test có bắt được lỗi không:** cố ý cài sai `>` thành `>=` thì 2 test đỏ; bỏ lời gọi `_burn` thì 6 test đỏ. Đã hoàn lại code đúng.

**Chưa làm / giới hạn:**
- HUD chưa có thanh "sắp cháy" trên bếp; người chơi chỉ thấy khi món đã cháy.
- Chưa chơi tay trọn một Ngày trong `chonoi.ngay_dem` có món cháy. Luật dùng chung `QuanSim` nên `day` cũng cháy (tất định `day` seed 1 đã chạy).
- Chạy test trên Windows cần lệnh `python3`; máy này dùng shim tạm (Python 3.11).

Lệnh tái lập:
```bash
PYTHONPATH=tests:. python3 -m unittest test_ext_burn -v
python3 -m chonoi.headless --mode quan --seed 1 --ticks 1600 --scenario docs/proof/ext-burn/flow-sc.json --inputs docs/proof/ext-burn/flow-inputs.json --out flow.jsonl
python3 tools/kiem_tat_dinh.py --mode quan --seed 1 --ticks 1600 --scenario docs/proof/ext-burn/flow-sc.json --inputs docs/proof/ext-burn/flow-inputs.json
```
