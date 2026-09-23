import csv

with open("data/location_lookup.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    admin_regions = sorted(set(row["administrative_region"].strip() for row in reader if row.get("administrative_region")))

print("Total unique administrative_region values:", len(admin_regions))
for r in admin_regions:
    print(r)
