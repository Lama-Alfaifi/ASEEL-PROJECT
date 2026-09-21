import csv

with open("data/raw/NORTH.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("Total rows:", len(rows))
print("Columns:", reader.fieldnames)
print()

suspicious = [r for r in rows if len(r.get("Answer", "").strip()) <= 3]

print(f"Rows with very short Answer (<=3 chars): {len(suspicious)}")
print()

for row in suspicious:
    print(row)
    print()
