from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import xmltodict

app = FastAPI(title="Flatway Spain Property Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

CATASTRO_BASE = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def catastro_get(endpoint, params):
    url = f"{CATASTRO_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return xmltodict.parse(r.content)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Catastro API timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# SEARCH BY ADDRESS — returns list, no bulk fetch
# ─────────────────────────────────────────────

@app.get("/search/address")
def search_by_address(
    street: str = Query(...),
    number: str = Query(...),
    municipality: str = Query(...),
    province: str = Query(...),
    street_type: str = Query(default="CL"),
):
    params = {
        "Provincia": province.upper(),
        "Municipio": municipality.upper(),
        "Sigla": street_type.upper(),
        "Calle": street.upper(),
        "Numero": number,
        "Bloque": "",
        "Escalera": "",
        "Planta": "",
        "Puerta": "",
    }
    data = catastro_get("Consulta_DNPLOC", params)
    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="No results found")

    # Single property — full detail already in response
    bico = root.get("bico", {})
    if bico:
        return {"count": 1, "properties": [format_bico(bico)]}

    # Multiple units — return lightweight list only, NO bulk fetch
    lrcdnp = root.get("lrcdnp", {})
    items = lrcdnp.get("rcdnp", [])
    if not isinstance(items, list):
        items = [items]

    results = [format_list_item(i) for i in items if i]
    return {"count": len(results), "properties": results}


# ─────────────────────────────────────────────
# GET SINGLE UNIT DETAIL — called on click
# ─────────────────────────────────────────────

@app.get("/property/{rc}")
def get_property(rc: str):
    """Fetch full detail for a single property by cadastral reference."""
    data = catastro_get("Consulta_DNPRC", {"Provincia": "", "Municipio": "", "RC": rc.upper()})
    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="Not found")
    bico = root.get("bico", {})
    if not bico:
        raise HTTPException(status_code=404, detail="Not found")
    return {"count": 1, "properties": [format_bico(bico)]}


# ─────────────────────────────────────────────
# SEARCH BY CADASTRAL REFERENCE
# ─────────────────────────────────────────────

@app.get("/search/ref")
def search_by_ref(
    rc: str = Query(...),
    province: str = Query(default=""),
    municipality: str = Query(default=""),
):
    params = {"Provincia": province.upper(), "Municipio": municipality.upper(), "RC": rc.upper()}
    data = catastro_get("Consulta_DNPRC", params)
    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="No results found")
    bico = root.get("bico", {})
    if not bico:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"count": 1, "properties": [format_bico(bico)]}


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
    parts = []
    if dir_.get("tv"): parts.append(dir_["tv"])
    if dir_.get("nv"): parts.append(dir_["nv"])
    if dir_.get("pnp"): parts.append(f"nº{dir_['pnp']}")
    loint = lourb.get("loint", {})
    if loint.get("es") and loint["es"] not in ("T", ""): parts.append(f"Esc.{loint['es']}")
    if loint.get("pt") and loint["pt"] not in ("OD", ""): parts.append(f"Pl.{loint['pt']}")
    if loint.get("pu") and loint["pu"] not in ("OS", ""): parts.append(f"Pta.{loint['pu']}")

    # construction breakdown
    lcons = bico.get("lcons", {})
    cons_list = lcons.get("cons", [])
    if not isinstance(cons_list, list):
        cons_list = [cons_list]
    constructions = []
    for c in cons_list:
        if c:
            constructions.append({
                "use": c.get("lcd"),
                "floor": c.get("dt", {}).get("lourb", {}).get("loint", {}).get("pt"),
                "door": c.get("dt", {}).get("lourb", {}).get("loint", {}).get("pu"),
                "surface_m2": c.get("dfcons", {}).get("stl"),
            })

    return {
        "cadastral_ref": ref or None,
        "address": " ".join(parts) or bi.get("ldt"),
        "municipality": dt.get("nm"),
        "province": dt.get("np"),
        "postal_code": lourb.get("dp"),
        "use": debi.get("luso"),
        "surface_m2": debi.get("sfc"),
        "year_built": debi.get("ant"),
        "cadastral_value": debi.get("vlr"),
        "coeff_participation": debi.get("cpt"),
        "constructions": constructions,
        "catastro_url": f"https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCConCiud.aspx?RefC={ref}" if ref else None,
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
    if loint.get("es") and loint["es"] not in ("T",""):  parts.append(f"Esc.{loint['es']}")
    if loint.get("pt") and loint["pt"] not in ("OD",""): parts.append(f"Pl.{loint['pt']}")
    if loint.get("pu") and loint["pu"] not in ("OS",""): parts.append(f"Pta.{loint['pu']}")
    return {
        "cadastral_ref": ref or None,
        "address": " ".join(parts) or None,
        "floor": loint.get("pt"),
        "door": loint.get("pu"),
        "municipality": np.get("nm") if isinstance(np, dict) else None,
        "province": np.get("np") if isinstance(np, dict) else None,
        "use": dt.get("luso"),
        "surface_m2": dt.get("sfc"),
        "year_built": dt.get("ant"),
        "catastro_url": f"https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCConCiud.aspx?RefC={ref}" if ref else None,
    }


@app.get("/")
def root():
    return {"status": "Flatway Spain property API running", "catastro": "direct (official)"}
