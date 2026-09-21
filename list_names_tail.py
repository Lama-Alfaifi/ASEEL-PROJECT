import re

with open("regions_tail.geojson", encoding="utf-8", errors="ignore") as f:
    content = f.read()

names = re.findall(r'"name_en":\s*"([^"]+)"', content)
print("Total regions found in tail:", len(names))
for n in names:
    print(n)
