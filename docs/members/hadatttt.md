# hadatttt — phản tư cá nhân (≤ 200 từ)

Hà Văn Khánh Đạt (2A202604074) · Vai: PO + Scrum/Release · vào nhóm từ Phase 3 (nhóm lên 5 người).

- Tôi đã làm (kèm link commit):
  - Điền `TEAM.md` theo việc thật của 5 người (đọc `git log`), đổi `team`/`team_size` trong `game.contract.json`.
  - Phát hiện `team_size: 5` kéo theo yêu cầu **ít nhất 1 mục mở rộng** (TICKET-02/03 mục Mở rộng), báo nhóm.
  - Làm trọn mở rộng **Cháy món** (`burn`), chia 7 commit `ext-burn`: kiểm manifest → luật `quan.py` → bật + 11 test
    → UI → hợp đồng/CHANGELOG/clarify → verification + bằng chứng → README/AGENTS. 172 test OK, tất định OK.
- Tôi đã review (kèm link): (cập nhật ở Phase 4)
- AI sai ở đâu và tôi phát hiện thế nào:
  - Lúc đầu AI viết lại hợp đồng kho v1.0 và một skill kiểm tất định trong khi `main` đã có bản v1.2 và skill `kiem-tat-dinh` của Shirou191. Phát hiện khi `git fetch` thấy 12 commit mới; bỏ 2 commit trùng, giữ lại ở nhánh `backup/hadatttt-p1` trên máy.
  - AI ghi E/Space là phím "giữ"; đọc `chonoi/sim/gather.py` thì luật bắt theo cạnh nhấn.
  - 11 test Cháy món qua ngay lần đầu, nên không tin ngay: cố ý cài sai luật (`>` thành `>=`, bỏ `_burn`) thì 2 và 6 test đỏ, chứng tỏ test thật sự bắt lỗi.
  - Lần kiểm UI đầu AI kết luận sai vì chụp màn hình trễ (hiệu ứng đã tắt) và gán đè hàm không có tác dụng; đổi sang theo dõi thẳng `QF.fx` mới thấy UI chạy đúng.
- Điều tôi học được: luôn `git fetch` trước khi bắt tay làm, nhất là khi nhóm push thẳng `main`.
