import requests, csv, time

API = "http://localhost:8000"

ADDRESSES = [
    {"street": "SERRANO", "number": "41", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "GRAN VIA", "number": "10", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "ALCALA", "number": "11", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "CASTELLANA", "number": "1", "municipality": "MADRID", "province": "MADRID", "street_type": "PS"},
    {"street": "FUENCARRAL", "number": "20", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "MAYOR", "number": "5", "municipality": "MADRID", "province": "MADRID", "street_type": "CL"},
    {"street": "DIAGONAL", "number": "10", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "AV"},
    {"street": "GRACIA", "number": "43", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "PS"},
    {"street": "RAMBLA", "number": "100", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "MALLORCA", "number": "10", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "BALMES", "number": "10", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "ROGER DE LLURIA", "number": "8", "municipality": "BARCELONA", "province": "BARCELONA", "street_type": "CL"},
    {"street": "SIERPES", "number": "5", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "CL"},
    {"street": "SAN FERNANDO", "number": "5", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "CL"},
    {"street": "REPUBLICA ARGENTINA", "number": "10", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "AV"},
    {"street": "BETIS", "number": "5", "municipality": "SEVILLA", "province": "SEVILLA", "street_type": "CL"},
    {"street": "COLON", "number": "10", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "PAZ", "number": "10", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "XATIVA", "number": "10", "municipality": "VALENCIA", "province": "VALENCIA", "street_type": "CL"},
    {"street": "MARQUES DE LARIOS", "number": "1", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},
    {"street": "VICTORIA", "number": "5", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},
    {"street": "CARRETERIA", "number": "5", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},
    {"street": "ALCAZABILLA", "number": "3", "municipality": "MALAGA", "province": "MALAGA", "street_type": "CL"},
    {"street": "INDEPENDENCIA", "number": "10", "municipality": "ZARAGOZA", "province": "ZARAGOZA", "street_type": "PS"},
    {"street": "COSO", "number": "5", "municipality": "ZARAGOZA", "province": "ZARAGOZA", "street_type": "CL"},
    {"street": "SANTIAGO", "number": "5", "municipality": "VALLADOLID", "province": "VALLADOLID", "street_type": "CL"},
    {"street": "REYES CATOLICOS", "number": "3", "municipality": "GRANADA", "province": "GRANADA", "street_type": "CL"},
    {"street": "MAYOR", "number": "4", "municipality": "SALAMANCA", "province": "SALAMANCA", "street_type": "CL"},
    {"street": "TRAPERIA", "number": "10", "municipality": "MURCIA", "province": "MURCIA", "street_type": "CL"},
    {"street": "CRUZ CONDE", "number": "5", "municipality": "CORDOBA", "province": "CORDOBA", "street_type": "CL"},
]

CSV_FIELDS = [
    "city","cadastral_ref","full_address","municipality","province","postal_code",
    "use","property_class","surface_m2","total_built_surface_m2","year_built",
    "num_floors_above_ground","floor","door","latitude","longitude",
    "cadastral_value","coeff_participation","use_types",
    "market_data_level","avg_rent_apt_m2_month","avg_rent_house_m2_month",
    "estimated_monthly_rent","estimated_market_value","estimated_price_m2",
    "ine_province_code","ine_municipality_code","street_type","street_name","street_number",
]

def flatten(prop):
    coords = prop.get("coordinates") or {}
    market = prop.get("market_data") or {}
    return {
        "city": prop.get("municipality",""), "cadastral_ref": prop.get("cadastral_ref",""),
        "full_address": prop.get("full_address",""), "municipality": prop.get("municipality",""),
        "province": prop.get("province",""), "postal_code": prop.get("postal_code",""),
        "use": prop.get("use",""), "property_class": prop.get("property_class",""),
        "surface_m2": prop.get("surface_m2",""), "total_built_surface_m2": prop.get("total_built_surface_m2",""),
        "year_built": prop.get("year_built",""), "num_floors_above_ground": prop.get("num_floors_above_ground",""),
        "floor": prop.get("floor",""), "door": prop.get("door",""),
        "latitude": coords.get("lat",""), "longitude": coords.get("lon",""),
        "cadastral_value": prop.get("cadastral_value",""), "coeff_participation": prop.get("coeff_participation",""),
        "use_types": ", ".join(prop.get("use_types") or []),
        "market_data_level": market.get("data_level",""),
        "avg_rent_apt_m2_month": market.get("avg_rent_apt_m2_month",""),
        "avg_rent_house_m2_month": market.get("avg_rent_house_m2_month",""),
        "estimated_monthly_rent": market.get("estimated_monthly_rent",""),
        "estimated_market_value": market.get("estimated_market_value",""),
        "estimated_price_m2": market.get("estimated_price_m2",""),
        "ine_province_code": prop.get("ine_province_code",""), "ine_municipality_code": prop.get("ine_municipality_code",""),
        "street_type": prop.get("street_type",""), "street_name": prop.get("street_name",""),
        "street_number": prop.get("street_number",""),
    }

results, failed = [], []
print(f"Querying {len(ADDRESSES)} addresses...\n")

for i, addr in enumerate(ADDRESSES):
    try:
        r = requests.get(f"{API}/search/address", params=addr, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("properties"):
            prop = data["properties"][0]
            results.append(flatten(prop))
            print(f"✅ {i+1}/{len(ADDRESSES)} {addr['municipality']} — {prop.get('full_address','found')}")
        else:
            failed.append(addr)
            print(f"❌ {i+1}/{len(ADDRESSES)} {addr['municipality']} {addr['street']} — not found")
    except Exception as e:
        failed.append(addr)
        print(f"❌ {i+1}/{len(ADDRESSES)} {addr['municipality']} {addr['street']} — error: {e}")
    time.sleep(0.5)

with open("flatway_spain_sample.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(results)

print(f"\n✅ Done! {len(results)} properties exported to flatway_spain_sample.csv")
print(f"❌ {len(failed)} failed")
