from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import xmltodict
import unicodedata
import re
import time

app = FastAPI(title="Flatway Spain Property Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

CATASTRO_BASE = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx"
CATASTRO_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Municipality name variations (Catalan/Spanish/regional differences)
MUNICIPALITY_VARIATIONS = {
    'alicante': ['ALICANTE', 'ALACANT'],
    'alacant': ['ALICANTE', 'ALACANT'],
    'valencia': ['VALENCIA', 'VALÈNCIA'],
    'lleida': ['LLEIDA', 'LÉRIDA'],
    'girona': ['GIRONA', 'GERONA'],
    'la coruña': ['A CORUÑA', 'LA CORUÑA'],
    'orense': ['OURENSE', 'ORENSE'],
    'san sebastián': ['SAN SEBASTIÁN', 'DONOSTIA'],
    'pamplona': ['PAMPLONA', 'IRUÑA'],
}

PROVINCE_MAP = {
    'comunidad de madrid': 'MADRID', 'madrid': 'MADRID',
    'cataluna': 'BARCELONA', 'cataluña': 'BARCELONA',
    'comunitat valenciana': 'VALENCIA', 'valencia': 'VALENCIA',
    'andalucia': 'SEVILLA', 'andalucía': 'SEVILLA',
    'aragon': 'ZARAGOZA', 'aragón': 'ZARAGOZA',
    'castilla y leon': 'VALLADOLID', 'castilla-la mancha': 'TOLEDO',
    'extremadura': 'BADAJOZ', 'galicia': 'PONTEVEDRA',
    'pais vasco': 'VIZCAYA', 'país vasco': 'VIZCAYA',
    'navarra': 'NAVARRA', 'la rioja': 'LOGRONO',
    'asturias': 'OVIEDO', 'cantabria': 'SANTANDER',
    'murcia': 'MURCIA', 'region de murcia': 'MURCIA',
    'islas baleares': 'ILLES BALEARS', 'illes balears': 'ILLES BALEARS',
    'alacant / alicante': 'ALICANTE', 'alicante': 'ALICANTE',
    'barcelona': 'BARCELONA', 'girona': 'GIRONA',
    'lleida': 'LLEIDA', 'tarragona': 'TARRAGONA',
    'sevilla': 'SEVILLA', 'malaga': 'MALAGA', 'málaga': 'MALAGA',
    'granada': 'GRANADA', 'cordoba': 'CORDOBA', 'córdoba': 'CORDOBA',
    'cadiz': 'CADIZ', 'cádiz': 'CADIZ', 'huelva': 'HUELVA',
    'almeria': 'ALMERIA', 'almería': 'ALMERIA', 'jaen': 'JAEN', 'jaén': 'JAEN',
    'zaragoza': 'ZARAGOZA', 'huesca': 'HUESCA', 'teruel': 'TERUEL',
    'valladolid': 'VALLADOLID', 'burgos': 'BURGOS', 'leon': 'LEON',
    'salamanca': 'SALAMANCA', 'segovia': 'SEGOVIA', 'avila': 'AVILA',
    'zamora': 'ZAMORA', 'palencia': 'PALENCIA', 'soria': 'SORIA',
    'toledo': 'TOLEDO', 'ciudad real': 'CIUDAD REAL', 'cuenca': 'CUENCA',
    'guadalajara': 'GUADALAJARA', 'albacete': 'ALBACETE',
    'caceres': 'CACERES', 'badajoz': 'BADAJOZ', 'pontevedra': 'PONTEVEDRA',
    'lugo': 'LUGO', 'ourense': 'ORENSE', 'vizcaya': 'VIZCAYA',
    'guipuzcoa': 'GUIPUZCOA', 'alava': 'ALAVA',
    'santa cruz de tenerife': 'SANTA CRUZ DE TENERIFE', 'las palmas': 'LAS PALMAS',
    'community of madrid': 'MADRID', 'autonomous community of madrid': 'MADRID',
    'catalonia': 'BARCELONA', 'valencian community': 'VALENCIA',
    'andalusia': 'SEVILLA', 'aragon': 'ZARAGOZA',
    'castile and leon': 'VALLADOLID', 'castile-la mancha': 'TOLEDO',
    'basque country': 'VIZCAYA', 'navarre': 'NAVARRA',
    'balearic islands': 'ILLES BALEARS', 'canary islands': 'LAS PALMAS',
    'region of murcia': 'MURCIA',
}

STREET_PREFIXES = [
    ('carretera de', 'CR'), ('carretera', 'CR'),
    ('avenida de la', 'AV'), ('avenida de los', 'AV'), ('avenida de las', 'AV'),
    ('avenida del', 'AV'), ('avenida de', 'AV'), ('avenida', 'AV'),
    ('paseo de la', 'PS'), ('paseo de los', 'PS'), ('paseo de las', 'PS'),
    ('paseo del', 'PS'), ('paseo de', 'PS'), ('paseo', 'PS'),
    ('plaza de la', 'PL'), ('plaza de los', 'PL'), ('plaza de las', 'PL'),
    ('plaza del', 'PL'), ('plaza de', 'PL'), ('plaza', 'PL'),
    ('ronda de', 'RD'), ('ronda', 'RD'),
    ('glorieta de', 'GL'), ('glorieta', 'GL'),
    ('travesia de', 'TR'), ('travesia', 'TR'),
    ('calle de la', 'CL'), ('calle de los', 'CL'), ('calle de las', 'CL'),
    ('calle del', 'CL'), ('calle de', 'CL'), ('calle', 'CL'),
    ('carrer de la', 'CL'), ('carrer de les', 'CL'), ('carrer dels', 'CL'),
    ('carrer del', 'CL'), ("carrer d'", 'CL'), ('carrer de', 'CL'), ('carrer', 'CL'),
    ('avinguda de', 'AV'), ('avinguda', 'AV'),
    ('passeig de', 'PS'), ('passeig', 'PS'),
]

# ─────────────────────────────────────────────
# SERPAVI RENTAL PRICE LOOKUP (pre-loaded)
# ─────────────────────────────────────────────
import json as _json2
import os as _os2

_SERPAVI = {}
_serpavi_file = _os2.path.join(_os2.path.dirname(__file__), 'serpavi_lookup.json')
try:
    with open(_serpavi_file, encoding='utf-8') as _f2:
        _SERPAVI = _json2.load(_f2)
    print(f"Loaded SERPAVI data for {len(_SERPAVI)} municipalities")
except Exception as e:
    print(f"Could not load SERPAVI data: {e}")

_SERPAVI_PROV = {}
_serpavi_prov_file = _os2.path.join(_os2.path.dirname(__file__), 'serpavi_provinces.json')
try:
    with open(_serpavi_prov_file, encoding='utf-8') as _f3:
        _SERPAVI_PROV = _json2.load(_f3)
    print(f"Loaded SERPAVI province data for {len(_SERPAVI_PROV)} provinces")
except Exception as e:
    print(f"Could not load SERPAVI province data: {e}")

def get_rental_data(ine_province_code: str, ine_municipality_code: str):
    if not ine_province_code:
        return None
    prov_code = ine_province_code.zfill(2)
    if ine_municipality_code:
        mun_code = prov_code + ine_municipality_code.zfill(3)
        data = _SERPAVI.get(mun_code)
        if data:
            return {**data, 'data_level': 'municipality'}
    prov_data = _SERPAVI_PROV.get(prov_code)
    if prov_data:
        return {**prov_data, 'data_level': 'province'}
    return None


def remove_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def normalize_province(raw):
    if not raw: return ''
    key = remove_accents(raw).lower().strip()
    return PROVINCE_MAP.get(key, remove_accents(raw).upper().strip())

def get_municipality_variations(municipality):
    """Return list of municipality name variations to try"""
    normalized = remove_accents(municipality).lower().strip()
    variations = MUNICIPALITY_VARIATIONS.get(normalized, [municipality.upper()])
    if municipality.upper() not in variations:
        variations.insert(0, municipality.upper())
    return variations

def parse_road(road):
    norm = remove_accents(road).lower().strip()
    for prefix, code in STREET_PREFIXES:
        if norm.startswith(prefix):
            name = road[len(prefix):].strip()
            name = re.sub(r'^(de la |de los |de las |del |de )', '', name, flags=re.IGNORECASE).strip()
            return code, remove_accents(name).upper().strip()
    return 'CL', remove_accents(road).upper().strip()

def catastro_get(endpoint, params, retry_delay=0.5):
    url = f"{CATASTRO_BASE}/{endpoint}"
    try:
        if retry_delay > 0:
            time.sleep(retry_delay)
        r = requests.get(url, params=params, headers=CATASTRO_HEADERS, timeout=8)
        r.raise_for_status()
        return xmltodict.parse(r.content)
    except Exception:
        return None


# ─────────────────────────────────────────────
# GEOCODING
# ─────────────────────────────────────────────

def get_coordinates(street_name, street_number, postal_code, municipality):
    try:
        q = f"{street_name} {street_number}, {postal_code}, {municipality}, Spain"
        r = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': q, 'format': 'json', 'limit': 1, 'countrycodes': 'es'},
            headers={'User-Agent': 'FlatwaySpainApp/1.0'},
            timeout=3,
        )
        if r.status_code == 200:
            results = r.json()
            if results:
                return {'lat': float(results[0]['lat']), 'lon': float(results[0]['lon'])}
        q2 = f"{postal_code}, {municipality}, Spain"
        r2 = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': q2, 'format': 'json', 'limit': 1, 'countrycodes': 'es'},
            headers={'User-Agent': 'FlatwaySpainApp/1.0'},
            timeout=3,
        )
        if r2.status_code == 200:
            results2 = r2.json()
            if results2:
                return {'lat': float(results2[0]['lat']), 'lon': float(results2[0]['lon']), 'precision': 'postal_code'}
    except Exception:
        pass
    return {}


# ─────────────────────────────────────────────
# AUTOCOMPLETE
# ─────────────────────────────────────────────

@app.get("/autocomplete")
def autocomplete(q: str = Query(...)):
    has_number = bool(re.search(r'\d', q))
    street_words = ['calle','avenida','paseo','plaza','carretera','ronda','glorieta','travesia','carrer','avinguda','passeig']
    q_lower = q.lower()
    if not any(q_lower.startswith(w) for w in street_words) and not has_number:
        nominatim_q = 'Calle ' + q
    else:
        nominatim_q = q

    try:
        r = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': nominatim_q, 'countrycodes': 'es', 'format': 'json', 'addressdetails': 1, 'limit': 10},
            headers={'User-Agent': 'FlatwaySpainApp/1.0'},
            timeout=5,
        )
        r.raise_for_status()
        results = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    suggestions = []
    seen = set()

    for item in results:
        addr = item.get('address', {})
        road = addr.get('road') or addr.get('pedestrian') or addr.get('footway')
        house = addr.get('house_number')
        city = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('municipality')
        postcode = addr.get('postcode', '')
        province = addr.get('province') or addr.get('state', '')

        if not road or not city:
            continue

        if has_number:
            if not house:
                continue
            key = f"{road}|{house}|{city}".lower()
            if key in seen:
                continue
            seen.add(key)
            label_parts = [road, house, postcode, city]
            if province and remove_accents(province).lower() != remove_accents(city).lower():
                label_parts.append(f"({province})")
            suggestions.append({
                'label': ', '.join(filter(None, label_parts)),
                'road': road, 'house_number': house, 'city': city,
                'postcode': postcode, 'province': province, 'type': 'address',
            })
        else:
            key = f"{road}|{city}".lower()
            if key in seen:
                continue
            seen.add(key)
            label_parts = [road, postcode, city]
            if province and remove_accents(province).lower() != remove_accents(city).lower():
                label_parts.append(f"({province})")
            suggestions.append({
                'label': ', '.join(filter(None, label_parts)),
                'road': road, 'house_number': None, 'city': city,
                'postcode': postcode, 'province': province, 'type': 'street',
            })

    return {'suggestions': suggestions[:8], 'type': 'street' if not has_number else 'address'}


# ─────────────────────────────────────────────
# IMPROVED SEARCH BY ADDRESS WITH RETRY LOGIC
# ─────────────────────────────────────────────

@app.get("/search/address")
def search_by_address(
    street: str = Query(...),
    number: str = Query(...),
    municipality: str = Query(...),
    province: str = Query(...),
    street_type: str = Query(default="CL"),
):
    clean_number = re.sub(r'\s*(bis|ter|[a-zA-Z]+)$', '', number, flags=re.IGNORECASE).strip()
    
    # Try municipality variations
    municipality_variations = get_municipality_variations(municipality)
    
    # Try different street types if not specified
    street_types_to_try = [street_type.upper()] if street_type and street_type != "CL" else ['CL', 'AV', 'PS', 'PL', 'CR']
    
    last_error = None
    attempts = []
    
    for mun_var in municipality_variations:
        for st_type in street_types_to_try:
            params = {
                "Provincia": province.upper(),
                "Municipio": mun_var,
                "Sigla": st_type,
                "Calle": street.upper(),
                "Numero": clean_number,
                "Bloque": "", "Escalera": "", "Planta": "", "Puerta": "",
            }
            
            attempt_key = f"{mun_var}_{st_type}"
            if attempt_key in attempts:
                continue
            attempts.append(attempt_key)
            
            data = catastro_get("Consulta_DNPLOC", params, retry_delay=0.3)
            if not data:
                last_error = "Catastro API unavailable"
                continue
                
            root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
            if not root:
                continue
            
            bico = root.get("bico", {})
            if bico:
                prop = format_bico(bico)
                prop["coordinates"] = get_coordinates(
                    prop.get("street_name", street),
                    prop.get("street_number", clean_number),
                    prop.get("postal_code", ""),
                    prop.get("municipality", municipality)
                )
                rental = get_rental_data(prop.get("ine_province_code"), prop.get("ine_municipality_code"))
                if rental:
                    prop["market_data"] = dict(rental)
                    surface = prop.get("total_built_surface_m2") or (int(prop.get("surface_m2", 0)) if prop.get("surface_m2") else None)
                    if surface:
                        rent_m2 = rental.get("avg_rent_apt_m2_month")
                        if rent_m2:
                            est_monthly_rent = round(rent_m2 * surface)
                            est_market_value = round(est_monthly_rent * 12 / 0.05)
                            est_price_m2 = round(est_market_value / surface)
                            prop["market_data"]["estimated_monthly_rent"] = est_monthly_rent
                            prop["market_data"]["estimated_market_value"] = est_market_value
                            prop["market_data"]["estimated_price_m2"] = est_price_m2
                return {"count": 1, "properties": [prop]}
            
            lrcdnp = root.get("lrcdnp", {})
            items = lrcdnp.get("rcdnp", [])
            if not isinstance(items, list): items = [items]
            if items and items[0]:
                results = [format_list_item(i) for i in items if i]
                return {"count": len(results), "properties": results}
            
            numerero = root.get("numerero", {})
            if numerero:
                nump = numerero.get("nump", [])
                if not isinstance(nump, list): nump = [nump]
                nearby = [n.get("num", {}).get("pnp") for n in nump if n.get("num", {}).get("pnp")]
                if nearby:
                    last_error = f"Number not found. Nearby: {', '.join(nearby[:5])}"
    
    # All attempts failed
    if last_error:
        raise HTTPException(status_code=404, detail=last_error)
    raise HTTPException(status_code=404, detail="Property not found after trying variations")


# ─────────────────────────────────────────────
# GET SINGLE PROPERTY BY REF
# ─────────────────────────────────────────────

@app.get("/property/{rc}")
def get_property(rc: str):
    data = catastro_get("Consulta_DNPRC", {"Provincia": "", "Municipio": "", "RC": rc.upper()})
    if not data:
        raise HTTPException(status_code=503, detail="Catastro API unavailable")
    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="Not found")
    bico = root.get("bico", {})
    if not bico:
        raise HTTPException(status_code=404, detail="Not found")
    prop = format_bico(bico)
    prop["coordinates"] = get_coordinates(
        prop.get("street_name", ""),
        prop.get("street_number", ""),
        prop.get("postal_code", ""),
        prop.get("municipality", "")
    )
    rental = get_rental_data(prop.get("ine_province_code"), prop.get("ine_municipality_code"))
    if rental:
        prop["market_data"] = dict(rental)
        surface = prop.get("total_built_surface_m2") or (int(prop.get("surface_m2", 0)) if prop.get("surface_m2") else None)
        if surface:
            rent_m2 = rental.get("avg_rent_apt_m2_month")
            if rent_m2:
                prop["market_data"]["estimated_monthly_rent"] = round(rent_m2 * surface)
                prop["market_data"]["estimated_market_value"] = round(rent_m2 * surface * 12 / 0.05)
                prop["market_data"]["estimated_price_m2"] = round(rent_m2 * surface * 12 / 0.05 / surface)
    return {"count": 1, "properties": [prop]}


@app.get("/search/ref")
def search_by_ref(rc: str = Query(...), province: str = Query(default=""), municipality: str = Query(default="")):
    params = {"Provincia": province.upper(), "Municipio": municipality.upper(), "RC": rc.upper()}
    data = catastro_get("Consulta_DNPRC", params)
    if not data:
        raise HTTPException(status_code=503, detail="Catastro API unavailable")
    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="No results found")
    bico = root.get("bico", {})
    if not bico:
        raise HTTPException(status_code=404, detail="Property not found")
    prop = format_bico(bico)
    prop["coordinates"] = get_coordinates(
        prop.get("street_name", ""),
        prop.get("street_number", ""),
        prop.get("postal_code", ""),
        prop.get("municipality", "")
    )
    rental = get_rental_data(prop.get("ine_province_code"), prop.get("ine_municipality_code"))
    if rental:
        prop["market_data"] = dict(rental)
        surface = prop.get("total_built_surface_m2") or (int(prop.get("surface_m2", 0)) if prop.get("surface_m2") else None)
        if surface:
            rent_m2 = rental.get("avg_rent_apt_m2_month")
            if rent_m2:
                prop["market_data"]["estimated_monthly_rent"] = round(rent_m2 * surface)
                prop["market_data"]["estimated_market_value"] = round(rent_m2 * surface * 12 / 0.05)
                prop["market_data"]["estimated_price_m2"] = round(rent_m2 * surface * 12 / 0.05 / surface)
    return {"count": 1, "properties": [prop]}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def format_bico(bico):
    bi = bico.get("bi", {})
    dt = bi.get("dt", {})
    debi = bi.get("debi", {})
    idbi = bi.get("idbi", {})
    rc = idbi.get("rc", {})
    ref = rc.get("pc1","") + rc.get("pc2","") + rc.get("car","") + rc.get("cc1","") + rc.get("cc2","")
    lourb = dt.get("locs", {}).get("lous", {}).get("lourb", {})
    dir_ = lourb.get("dir", {})
    loint = lourb.get("loint", {})
    parts = []
    if dir_.get("tv"): parts.append(dir_["tv"])
    if dir_.get("nv"): parts.append(dir_["nv"])
    if dir_.get("pnp"): parts.append(f"nº{dir_['pnp']}")
    if loint.get("es") and loint["es"] not in ("T", ""): parts.append(f"Esc.{loint['es']}")
    if loint.get("pt") and loint["pt"] not in ("OD", ""): parts.append(f"Pl.{loint['pt']}")
    if loint.get("pu") and loint["pu"] not in ("OS", ""): parts.append(f"Pta.{loint['pu']}")
    loine = dt.get("loine", {})
    lcons = bico.get("lcons", {})
    cons_list = lcons.get("cons", [])
    if not isinstance(cons_list, list): cons_list = [cons_list]
    constructions = []
    total_built = 0
    floors = set()
    use_types = set()
    for c in cons_list:
        if c:
            floor = c.get("dt", {}).get("lourb", {}).get("loint", {}).get("pt")
            door = c.get("dt", {}).get("lourb", {}).get("loint", {}).get("pu")
            surface = c.get("dfcons", {}).get("stl")
            use = c.get("lcd")
            if surface:
                try: total_built += int(surface)
                except: pass
            if floor: floors.add(floor)
            if use: use_types.add(use)
            constructions.append({"use": use, "floor": floor, "door": door, "surface_m2": surface})
    above_ground = [f for f in floors if f and not f.startswith('-') and f not in ('OD',)]
    return {
        "cadastral_ref": ref or None,
        "property_class": idbi.get("cn"),
        "address": " ".join(parts) or bi.get("ldt"),
        "full_address": bi.get("ldt"),
        "street_type": dir_.get("tv"),
        "street_name": dir_.get("nv"),
        "street_number": dir_.get("pnp"),
        "block": loint.get("es") if loint.get("es") not in ("T","") else None,
        "floor": loint.get("pt") if loint.get("pt") not in ("OD","") else None,
        "door": loint.get("pu") if loint.get("pu") not in ("OS","") else None,
        "municipality": dt.get("nm"),
        "province": dt.get("np"),
        "postal_code": lourb.get("dp"),
        "street_code": dir_.get("cv"),
        "municipality_catastro_code": dt.get("cmc"),
        "ine_province_code": loine.get("cp"),
        "ine_municipality_code": loine.get("cm"),
        "use": debi.get("luso"),
        "surface_m2": debi.get("sfc"),
        "year_built": debi.get("ant"),
        "cadastral_value": debi.get("vlr"),
        "coeff_participation": debi.get("cpt"),
        "total_built_surface_m2": total_built if total_built > 0 else None,
        "num_floors_above_ground": len(above_ground) if above_ground else None,
        "use_types": list(use_types) if use_types else None,
        "constructions": constructions,
    }


def format_list_item(item):
    rc = item.get("rc", {})
    ref = rc.get("pc1","") + rc.get("pc2","") + rc.get("car","") + rc.get("cc1","") + rc.get("cc2","")
    dt = item.get("dt", {})
    np = dt.get("np", {})
    locs = dt.get("locs", {}).get("lous", {}).get("loui", {})
    if isinstance(locs, list): locs = locs[0]
    dir_ = locs.get("dir", {}) if locs else {}
    loint = locs.get("loint", {}) if locs else {}
    parts = []
    if dir_.get("tv"): parts.append(dir_["tv"])
    if dir_.get("nv"): parts.append(dir_["nv"])
    if dir_.get("pnp"): parts.append(f"nº{dir_['pnp']}")
    if loint.get("es") and loint["es"] not in ("T",""): parts.append(f"Esc.{loint['es']}")
    if loint.get("pt") and loint["pt"] not in ("OD",""): parts.append(f"Pl.{loint['pt']}")
    if loint.get("pu") and loint["pu"] not in ("OS",""): parts.append(f"Pta.{loint['pu']}")
    return {
        "cadastral_ref": ref or None,
        "address": " ".join(parts) or None,
        "floor": loint.get("pt") if loint.get("pt") not in ("OD","") else None,
        "door": loint.get("pu") if loint.get("pu") not in ("OS","") else None,
        "municipality": np.get("nm") if isinstance(np, dict) else None,
        "province": np.get("np") if isinstance(np, dict) else None,
        "use": dt.get("luso"),
        "surface_m2": dt.get("sfc"),
        "year_built": dt.get("ant"),
    }


@app.get("/")
def root():
    return {"status": "Flatway Spain property API running"}
