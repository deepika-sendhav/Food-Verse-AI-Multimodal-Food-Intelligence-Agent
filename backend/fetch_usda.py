import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("USDA_FDC_API_KEY")
JSON_PATH = "backend/data/nutrition_reference.json"

# name: (USDA search text, aliases, default serving in grams)
FOODS = {
    "boiled chickpeas": ("chickpeas mature seeds cooked boiled", ["chickpeas", "chickpea", "chana", "chole", "cooked chickpeas"], 160),
    "boiled potato": ("potatoes white flesh and skin boiled cooked", ["potato", "potatoes", "boiled potato"], 150),
    "raw cucumber": ("cucumber raw", ["cucumber", "cucumbers", "sliced cucumber"], 50),
    "raw onion": ("onions raw", ["onion", "red onion", "sliced onion"], 30),
    "plain yogurt": ("yogurt plain whole milk", ["yogurt", "curd", "dahi", "raita"], 150),
}

IDS = {1008: "calories_kcal", 1003: "protein_g", 1005: "carbs_g",
       1004: "fats_g", 1079: "fiber_g", 2000: "sugar_g"}

def fetch(query):
    r = httpx.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={"api_key": KEY, "query": query, "pageSize": 5,
                "dataType": ["Foundation", "SR Legacy"]},
        timeout=15,
    )
    r.raise_for_status()
    for food in r.json().get("foods", []):
        values = {}
        for n in food.get("foodNutrients", []):
            field = IDS.get(n.get("nutrientId"))
            if field and n.get("value") is not None:
                values[field] = float(n["value"])
        if len(values) == 6:
            return food, values
    return None, None

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

for name, (query, aliases, serving) in FOODS.items():
    food, values = fetch(query)
    if not food:
        print(f"SKIPPED (no complete match): {name}")
        continue
    data[name] = {
        "aliases": aliases,
        "default_serving_g": serving,
        **values,
        "source": f"USDA FDC {food['fdcId']}: {food['description']}",
    }
    print(f"ADDED: {name} -> {food['description']} (FDC {food['fdcId']})")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)