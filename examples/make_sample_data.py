"""Generate examples/sample_canteen_orders.csv - a SYNTHETIC dataset.

None of these orders are real. The numbers come from Python's random module
with a fixed seed, so running this script always produces the same file.
A few problems are added on purpose, so the tool has something to find:
  * some missing ratings and missing payment methods
  * three rows that are exact duplicates of earlier rows

Run from the repository root:  python examples/make_sample_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)

MENU = {  # item: (category, price in rupees)
    "Masala Dosa": ("Meal", 60), "Veg Thali": ("Meal", 90), "Paneer Roll": ("Snack", 70),
    "Samosa": ("Snack", 20), "Veg Puff": ("Snack", 25), "Filter Coffee": ("Beverage", 25),
    "Cold Coffee": ("Beverage", 50), "Lime Soda": ("Beverage", 30),
}
COUNTERS = ["Main Canteen", "Food Court", "Juice Bar"]
PAYMENTS = ["UPI", "UPI", "UPI", "Cash", "Card"]  # UPI listed 3x = picked more often

rows = []
start = date(2026, 9, 1)
for order_id in range(1, 121):
    item = random.choice(list(MENU))
    category, price = MENU[item]
    quantity = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
    rows.append({
        "order_id": order_id,
        "date": (start + timedelta(days=random.randint(0, 55))).isoformat(),
        "counter": "Juice Bar" if category == "Beverage" and random.random() < 0.5
                   else random.choice(COUNTERS[:2]),
        "item": item,
        "category": category,
        "quantity": quantity,
        "unit_price_inr": price,
        "total_inr": price * quantity,
        "payment": random.choice(PAYMENTS) if random.random() > 0.04 else "",
        "rating": random.choice([3, 4, 4, 5, 5]) if random.random() > 0.15 else "",
    })

rows.sort(key=lambda r: (r["date"], r["order_id"]))
for copy_of in (12, 57, 98):  # deliberate duplicates
    rows.insert(copy_of + 5, dict(rows[copy_of]))

out = Path(__file__).with_name("sample_canteen_orders.csv")
with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} rows to {out}")
