"""
Flatway Spain — Sample Property Data Export
Queries 30 properties across major Spanish cities and exports to CSV.
Run with: python3 generate_sample_csv.py
Make sure uvicorn is running first: uvicorn main:app --reload
"""

import requests
import csv
import time
import json

API = "http://localhost:8000"

# 30 addresses across Spain's major cities
ADDRESSES = [
    # Madrid
    {"street": "SERRANO", "number": "41", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "GRAN VIA", "number": "10", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "ALCALA", "number": "11", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "CASTELLANA", "number": "1", "municipality": "MADRID", "province": "MADRID", "street_type": "PS"},
    {"street": "FUENCARRAL", "number": "10", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "MAYOR", "number": "5", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},

    # Barcelona
    {"street": "DIAGONAL", "number": "10", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "AV"},
    {"street": "GRACIA", "number": "43", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "PS"},
    {"street": "RAMBLA", "number": "100", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "ARAGON", "number": "20", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "BALMES", "number": "10", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},

    # Sevilla
    {"street": "SIERPES", "number": "5", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "CL"},
    {"street": "CONSTITUCION", "number": "1", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "AV"},
    {"street": "REPUBLICA ARGENTINA", "number": "10", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "AV"},
    {"street": "BETIS", "number": "5", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "CL"},

    # Valencia
    {"street": "COLON", "number": "10", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "BARON DE CARCER", "number": "5", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "PAZ", "number": "10", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "XATIVA", "number": "5", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},

    # Málaga
    {"street": "LARIOS", "number": "2", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},
    {"street": "CONSTITUCION", "number": "5", "municipality": "MALAGA", "province": "MALAGA", "street_type": "AV"},
    {"street": "GRANADA", "number": "10", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},

    # Bilbao
    {"street": "GRAN VIA", "number": "10", "municipality": "BILBAO", "province": "VIZCAYA", "street_type": "CL"},
    {"street": "AUTONOMIA", "number": "5", "municipality": "BILBAO", "province": "VIZCAYA", "street_type": "CL"},

    # Zaragoza
    {"street": "INDEPENDENCIA", "number": "10", "municipality": "ZARAGOZA", "province": "ZARAGOZA", "street_type": "PS"},
    {"street": "ARAGON", "number": "5", "municipality": "ZARAGOZA", "province": "ZARAGOZA", "street_type": "CL"},

    # Valladolid
    {"street": "SANTIAGO", "number": "10", "municipality": "VALLADOLID", "province": "VALLADOLID", "street_type": "CL"},

    # Alicante
    {"street": "EXPLANADA DE ESPANA", "number": "1", "municipality": "ALICANTE", "province": "ALICANTE", "street_type": "CL"},

    # Granada
    {"street": "REYES CATOLICOS", "number": "5", "municipality": "GRANADA", "province": "GRANADA", "street_type": "CL"},

    # Salamanca
    {"street": "MAYOR", "number": "10", "municipality": "SALAMANCA", "province": "SALAMANCA", "street_type": "PL"},
]

CSV_FIELDS = [
    "city", "cadastral_ref", "full_address", "municipality", "province", "postal_code",
    "use", "property_class", "surface_m2", "total_built_surface_m2", "year_built",
    "num_floors_above_ground", "floor", "door",
    "latitude", "longitude",
    "cadastral_value", "coeff_participation",
    "use_types",
    "market_data_level", "avg_rent_apt_m2_month", "avg_rent_house_m2_month",
    "estimated_monthly_rent", "estimated_market_value", "estimated_price_m2",
    "ine_province_code", "ine_municipality_code",
    "street_type", "street_name", "street_number",
]

def flatten(prop):
    coords = prop.get("coordinates") or {}
    market = prop.get("market_data") or {}
    use_types = prop.get("use_types") or []
    return {
        "city": prop.get("municipality", ""),
        "cadastral_ref": prop.get("cadastral_ref", ""),
        "full_address": prop.get("full_address", ""),
        "municipality": prop.get("municipality", ""),
        "province": prop.get("province", ""),
        "postal_code": prop.get("postal_code", ""),
        "use": prop.get("use", ""),
        "property_class": prop.get("property_class", ""),
        "surface_m2": prop.get("surface_m2", ""),
        "total_built_surface_m2": prop.get("total_built_surface_m2", ""),
        "year_built": prop.get("year_built", ""),
        "num_floors_above_ground": prop.get("num_floors_above_ground", ""),
        "floor": prop.get("floor", ""),
        "door": prop.get("door", ""),
        "latitude": coords.get("lat", ""),
        "longitude": coords.get("lon", ""),
        "cadastral_value": prop.get("cadastral_value", ""),
        "coeff_participation": prop.get("coeff_participation", ""),
        "use_types": ", ".join(use_types),
        "market_data_level": market.get("data_level", ""),
        "avg_rent_apt_m2_month": market.get("avg_rent_apt_m2_month", ""),
        "avg_rent_house_m2_month": market.get("avg_rent_house_m2_month", ""),
        "estimated_monthly_rent": market.get("estimated_monthly_rent", ""),
        "estimated_market_value": market.get("estimated_market_value", ""),
        "estimated_price_m2": market.get("estimated_price_m2", ""),
        "ine_province_code": prop.get("ine_province_code", ""),
        "ine_municipality_code": prop.get("ine_municipality_code", ""),
        "street_type": prop.get("street_type", ""),
        "street_name": prop.get("street_name", ""),
        "street_number": prop.get("street_number", ""),
    }

results = []
failed = []

print(f"Querying {len(ADDRESSES)} addresses...\n")

for i, addr in enumerate(ADDRESSES):
    url = f"{API}/search/address"
    params = {
        "street": addr["street"],
        "number": addr["number"],
        "municipality": addr["municipality"],
        "province": addr["province"],
        "street_type": addr["street_type"],
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("properties"):
            # Take first property if multiple units
            prop = data["properties"][0]
            results.append(flatten(prop))
            print(f"✅ {i+1}/30 {addr['municipality']} — {prop.get('full_address', 'found')}")
        else:
            failed.append(addr)
            print(f"❌ {i+1}/30 {addr['municipality']} {addr['street']} {addr['number']} — not found")
    except Exception as e:
        failed.append(addr)
        print(f"❌ {i+1}/30 {addr['municipality']} {addr['street']} — error: {e}")
    time.sleep(0.5)  # Be polite to Catastro

# Write CSV
output_file = "flatway_spain_sample.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(results)

print(f"\n✅ Done! {len(results)} properties exported to {output_file}")
print(f"❌ {len(failed)} addresses not found")
