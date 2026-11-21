"""Pha Shop cuối Ngày (chỉ có trong chế độ `day`). TICKET-02 mục 2 "Shop và nâng cấp", Test Contract v1.1 mục 4.5.

Một bước:
  1. Đồng hồ: `phase_tick` +1, `time_left_ticks` −1 (tự đóng sau `shop.max_ticks` bước hoạt động).
  2. Một lệnh `buy` (chỉ tại frame khai báo) TRƯỚC cạnh `shop_done`, kể cả bước cuối.
     Mua cấp kế tiếp: đủ đúng giá vẫn mua được; trừ `money`, giữ `earned`. Cấp mua hiển thị ngay
     (`upgrades`), có hiệu lực từ Ngày kế (DaySim sao sang `active_upgrades` khi dựng Ngày mới).
     Thất bại -> `buy_failed` với `max_level` / `funds` / `unknown` (lệnh không hỗ trợ hoặc mở rộng chưa bật).
  3. Cạnh `shop_done` -> `shop_end(done)`; ngược lại hết giờ -> `shop_end(time)`.
`stock` là kho dư từ ca quán (chỉ để xem, bị bỏ khi sang Ngày mới).
"""


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades):
        self.shop = tuning["shop"]
        self.stock = dict(stock)
        self.money = money
        self.earned = earned
        self.reputation = reputation
        self.upgrades = upgrades  # map dùng chung với DaySim: cấp vừa mua hiện ngay
        self.time_left_ticks = int(self.shop["max_ticks"])
        self.phase_tick = 0
        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        return {"stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}}

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy is not None:
            self._buy(inp.buy, events)
        if inp.pressed("shop_done"):
            self._end("done", events)
        elif self.time_left_ticks <= 0:
            self._end("time", events)
        return events

    def _buy(self, action, events):
        levels = self.shop["upgrades"].get(action)
        if levels is None:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        nxt = self.upgrades.get(action, 0) + 1
        if nxt > len(levels):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        price = int(levels[nxt - 1]["price"])
        if self.money < price:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        self.upgrades[action] = nxt
        events.append(("bought", {"upgrade": action, "level": nxt, "price": price, "money": self.money}))

    def _end(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("shop_end", {"reason": reason}))
