# Credits
Liệt kê asset ngoài (nguồn, giấy phép CC0/CC-BY/MIT) và công cụ AI đã dùng.

## Asset ngoài
Chưa dùng asset ngoài. Toàn bộ hình (Út Sen, cá, bông, nhà bè, quán, HUD bảng gỗ, icon) được vẽ thủ tục bằng Canvas 2D trong `chonoi/web/index.html`.

## Công cụ AI
| Công cụ | Dùng cho | Ghi chú |
|---|---|---|
| Claude Code (Claude Opus 5.5) | Skill `.agents/skills/thiet-ke-do-hoa`, code đồ họa/HUD/thoại trong `chonoi/web/index.html`, `tools/choi_ngay_dem.py` | Người trong nhóm duyệt trước khi commit. Phong cách quán buổi tối tham khảo một ảnh mẫu nhóm tự đưa; ảnh không được đưa vào repo hay dùng làm asset. |
| Claude Code (Claude Opus 5.5) | Phase 2–4 (Duc1306 + TADIZB): luật gather/quán v1.1, kho cá thể v1.2, `chonoi/bench.py`, `chonoi/soak.py`, cảnh báo + tương phản cao, test, tài liệu | Người trong nhóm đọc lại, chạy test trước khi commit; chi tiết ở `docs/ai-usage-log.md`. |

## Rà soát v1.0.0 (2026-11-21)
- Không có ảnh, âm thanh, font hay thư viện ngoài nào được đóng gói. Font chữ dùng font hệ thống (`Trebuchet MS`, `Segoe UI`, `system-ui`). Biểu tượng cảnh báo vẽ bằng canvas.
- Ảnh trong `docs/proof/` là ảnh chụp màn hình game của nhóm.
- Benchmark gọi trình duyệt có sẵn trên máy (Chromium/Chrome/Edge). Trình duyệt không được đóng gói kèm.
