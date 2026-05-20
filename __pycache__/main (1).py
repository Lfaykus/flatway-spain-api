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


def catastro_get(endpoint: str, params: dict) -> dict:
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
# SEARCH BY ADDRESS
# ─────────────────────────────────────────────

@app.get("/search/address")
def search_by_address(
    street: str = Query(..., description="Street name e.g. GRAN VIA"),
    number: str = Query(..., description="Street number e.g. 10"),
    municipality: str = Query(..., description="Municipality e.g. MADRID"),
    province: str = Query(..., description="Province e.g. MADRID"),
    street_type: str = Query(default="CL", description="Street type: CL=Calle, AV=Avenida, PS=Paseo, CR=Carretera etc."),
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
    print("RAW:", data)

    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="No results found")

    lerr = root.get("control", {})
    if lerr.get("cuerr", "0") != "0":
        err_desc = root.get("lerr", {}).get("err", {}).get("des", "Unknown error")
        raise HTTPException(status_code=404, detail=err_desc)

    bico = root.get("bico", {})
    if not bico:
        lrcdnp = root.get("lrcdnp", {})
        items = lrcdnp.get("rcdnp", [])
        if not isinstance(items, list):
            items = [items]
        return {
            "count": len(items),
            "properties": [format_list_item(i) for i in items if i],
        }

    return {
        "count": 1,
        "properties": [format_bico(bico)],
    }


# ─────────────────────────────────────────────
# SEARCH BY CADASTRAL REFERENCE
# ─────────────────────────────────────────────

@app.get("/search/ref")
def search_by_ref(
    rc: str = Query(..., description="Cadastral reference e.g. 9872023VH5797S0001WX"),
    province: str = Query(default="", description="Province name"),
    municipality: str = Query(default="", description="Municipality name"),
):
    params = {
        "Provincia": province.upper(),
        "Municipio": municipality.upper(),
        "RC": rc.upper(),
    }
    data = catastro_get("Consulta_DNPRC", params)
    print("RAW:", data)

    root = data.get("consulta_dnp") or data.get("Consulta_DNP", {})
    if not root:
        raise HTTPException(status_code=404, detail="No results found")

    bico = root.get("bico", {})
    if not bico:
        raise HTTPException(status_code=404, detail="Property not found for that reference")

    return {"count": 1, "properties": [format_bico(bico)]}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def format_bico(bico: dict) -> dict:
    bi = bico.get("bi", {})
    ubi = bi.get("ubi", {})
    debi = bi.get("debi", {})
    idbi = bi.get("idbi", {})
    rc = idbi.get("rc", {})
    ref = (rc.get("pc1","") + rc.get("pc2","") + rc.get("car","") + rc.get("cc1","") + rc.get("cc2",""))

    locs = ubi.get("locs", {}).get("lous", {}).get("loui", {})
    if isinstance(locs, list):
        locs = locs[0]
    dir_ = locs.get("dir", {}) if locs else {}

    address_parts = []
    if dir_.get("tv"): address_parts.append(dir_["tv"])
    if dir_.get("nv"): address_parts.append(dir_["nv"])
    if dir_.get("pnp"): address_parts.append(f"nº{dir_['pnp']}")

    return {
        "cadastral_ref": ref or None,
        "address": " ".join(address_parts) or None,
        "municipality": ubi.get("nm"),
        "province": ubi.get("np"),
        "postal_code": ubi.get("dp"),
        "use": debi.get("luso"),
        "surface_m2": debi.get("sfc"),
        "year_built": debi.get("ant"),
        "cadastral_value": debi.get("vlr"),
        "catastro_url": f"https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCConCiud.aspx?del=&mun=&RefC={ref}" if ref else None,
    }


def format_list_item(item: dict) -> dict:
    rc = item.get("rc", {})
    ref = (rc.get("pc1","") + rc.get("pc2","") + rc.get("car","") + rc.get("cc1","") + rc.get("cc2",""))
    dt = item.get("dt", {})
    np = dt.get("np", {})

    locs = dt.get("locs", {}).get("lous", {}).get("loui", {})
    if isinstance(locs, list):
        locs = locs[0]
    dir_ = locs.get("dir", {}) if locs else {}

    address_parts = []
    if dir_.get("tv"): address_parts.append(dir_["tv"])
    if dir_.get("nv"): address_parts.append(dir_["nv"])
    if dir_.get("pnp"): address_parts.append(f"nº{dir_['pnp']}")

    return {
        "cadastral_ref": ref or None,
        "address": " ".join(address_parts) or None,
        "municipality": np.get("nm") if isinstance(np, dict) else None,
        "province": np.get("np") if isinstance(np, dict) else None,
        "use": dt.get("luso"),
        "surface_m2": dt.get("sfc"),
        "year_built": dt.get("ant"),
        "catastro_url": f"https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCConCiud.aspx?del=&mun=&RefC={ref}" if ref else None,
    }


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Flatway Spain property API running", "catastro": "direct (official)"}
