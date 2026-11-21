# Thử chạy từ bản sạch (v1.0.0)

Ngày 2026-11-21, Windows 11 + Git Bash, Python 3.12. Bản sạch = `git archive` cây tree `f32b405a…` (đã gộp mở rộng Cháy món của nhóm; khác commit bàn giao chỉ ở tài liệu/số liệu cập nhật sau lần chạy này, code và test giống hệt), giải nén vào thư mục tạm (không có file ngoài repo, không `pip install`). Lệnh chơi theo README: `git clone …` → `cd …` → `python3 -m chonoi.ngay_dem` (3 lệnh). **Chưa thử trên máy macOS/Linux thật**; code chỉ dùng thư viện chuẩn Python.

Ghi chú: lúc chạy lần này máy đang bận (soak 15.7 s so với 8 s ở lần chạy riêng), nên FPS bench thấp hơn [bench.json](bench.json).

```text
## 1. python3 -m chonoi.ngay_dem --port 8765
GET / -> 164612 byte HTML; GET /state -> mode day phase gather day 1
Mở trình duyệt tại http://127.0.0.1:8765/  (chơi 5 Ngày, seed 1). Ctrl+C để dừng.
(đã dừng máy chủ)

## 2. PYTHONPATH=tests:. python3 -m unittest discover -s tests
Ran 200 tests in 49.564s

OK

## 3. python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl
exit=0
{"type":"end","ticks":22200,"sim_tick":22200,"mode":"day","state":"finished","reason":"days_complete","money":0,"earned":0,"reputation":3.0,"score":300,"days_completed":1}

## 4. python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
soak ĐẠT: 10/10 Ngày, crashes 0, 15.728 s
exit=0

## 5. python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json
bench: {"avg_fps": 22.96, "p1_low_fps": 14.37, "frames": 690, "measured_s": 30.049, "load_ms": 1337} — mốc báo cáo (avg ≥ 60, 1% low ≥ 30, load ≤ 10 s): chưa đạt · trình duyệt C:\Program Files\Google\Chrome\Application\chrome.exe
exit=0
{"avg_fps": 22.96, "p1_low_fps": 14.37, "frames": 690, "measured_s": 30.049, "load_ms": 1337}
```
