import json

path = "c:/Users/User/Desktop/colman/final_project/Lessley/lessley-deals/data/stores.json"

with open(path, "r", encoding="utf-8") as f:
    stores = json.load(f)

for store in stores:
    metadata = store.get("metadata", {})
    if "image_urls" in metadata:
        del metadata["image_urls"]
        store["metadata"] = metadata

with open(path, "w", encoding="utf-8") as f:
    json.dump(stores, f, ensure_ascii=False, indent=2)

print("Cleaned stores.json")
