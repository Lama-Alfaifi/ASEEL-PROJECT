with open("regions.geojson", encoding="utf-8", errors="ignore") as f:
    content = f.read()

idx = content.find('"properties"')
print("Found at position:", idx)
print()
print(content[idx-50:idx+400])
