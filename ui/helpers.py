import streamlit as st
import gspread
import pandas as pd
from database.crud.operaciones import obtener_operacion_completa

@st.cache_resource(ttl=3600)
def get_gspread_client() -> gspread.Client:
    credentials = st.secrets["google_sheets_credentials"]
    return gspread.service_account_from_dict(credentials)


def get_worksheet(sheet_id: str, sheet_name: str) -> gspread.Worksheet | None:
    gc = get_gspread_client()
    try:
        ss = gc.open_by_key(sheet_id)
        if sheet_name not in (ws.title for ws in ss.worksheets()):
            st.error(f"❌ La pestaña '{sheet_name}' no existe en la hoja.")
            return None
        return ss.worksheet(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ No se encontró la hoja de cálculo con el ID proporcionado.")
    except Exception as e:
        st.error(f"❌ Error al conectar a Google Sheets: {e}")
    return None


@st.cache_data(ttl=3600)
def load_clients() -> list[str]:
    sheet_id   = st.secrets["general"]["time_sheet_id"]
    sheet_name = "clientes"

    ws = get_worksheet(sheet_id, sheet_name)
    if ws is None:
        return []

    clientes = ws.col_values(1)    # primera columna
    return clientes[1:]            # omite encabezado

@st.cache_data(ttl=3600)
def load_clients_finance() -> pd.DataFrame:
    sheet_id   = st.secrets["general"]["data_clientes"]
    sheet_name = "clientes"

    ws = get_worksheet(sheet_id, sheet_name)
    if ws is None:
        return pd.DataFrame()

    data = ws.get_all_records()
    return pd.DataFrame(data)


def user_data(commercial):
    users = {
        "Sharon Zuñiga": {
            "name": "Sharon Zuñiga",
            "tel": "+57 (300) 510 0295",
            "position": "Business Development Manager Latam & USA",
            "email": "sales2@tradingsolutions.com"
        },
        "Irina Paternina": {
            "name": "Irina Paternina",
            "tel": "+57 (301) 3173340",
            "position": "Business Executive",
            "email": "sales1@tradingsolutions.com"
        },
        "Johnny Farah": {
            "name": "Johnny Farah",
            "tel": "+57 (301) 6671725",
            "position": "Manager of Americas",
            "email": "sales3@tradingsolutions.com"
        },
        "Jorge Sánchez": {
            "name": "Jorge Sánchez",
            "tel": "+57 (301) 7753510",
            "position": "Reefer Department Manager",
            "email": "sales4@tradingsolutions.com"
        },
        "Pedro Luis Bruges": {
            "name": "Pedro Luis Bruges",
            "tel": "+57 (304) 4969358",
            "position": "Global Sales Manager",
            "email": "sales@tradingsolutions.com"
        },
        "Ivan Zuluaga": {
            "name": "Ivan Zuluaga",
            "tel": "+57 (300) 5734657",
            "position": "Business Development Manager Latam & USA",
            "email": "sales5@tradingsolutions.com"
        },
        "Andrés Consuegra": { 
            "name": "Andrés Consuegra",
            "tel": "+57 (301) 7542622",
            "position": "CEO",
            "email": "manager@tradingsolutions.com"
        },
        "Stephanie Bruges": {
            "name": "Stephanie Bruges",
            "tel": "+57 300 4657077",
            "position": "Business Development Specialist",
            "email": "bds@tradingsolutions.com"
        },
        "Catherine Silva": {
            "name": "Catherine Silva",
            "tel": "+57 304 4969351",
            "position": "Inside Sales",
            "email": "insidesales@tradingsolutions.com"
        }
    }

    return users.get(commercial, {"name": commercial, "position": "N/A", "tel": "N/A", "email": "N/A"})


def cargar_operacion_en_formulario(no_solicitud):
    """
    Carga en st.session_state todos los datos relacionados a una operación existente:
    - Datos de la operación (comercial, comentarios)
    - Datos de la carga (BL/AWB, shipper, consignee, contenedores o carga suelta)
    - Ventas (sales_blocks) desde ventas_master y ventas_detalle
    - Costos (cost_surcharges)
    """
    datos_previos = obtener_operacion_completa(no_solicitud)
    if not datos_previos:
        return False  # No existe la operación

    operacion = datos_previos.get("operacion", {})
    carga = datos_previos.get("carga", {})
    ventas = datos_previos.get("ventas", [])  # ahora es ventas_master con detalles
    costos = datos_previos.get("costos", [])

    # --- Datos de la operación ---
    st.session_state["commercial"] = operacion.get("comercial", "")

    # --- Datos de la carga ---
    st.session_state["bl_awb"] = carga.get("bl_awb", "")
    st.session_state["shipper"] = carga.get("shipper", "")
    st.session_state["consignee"] = carga.get("consignee", "")
    st.session_state["pol_aol"] = carga.get("pol_aol", "")
    st.session_state["pod_aod"] = carga.get("pod_aod", "")
    st.session_state["reference"] = carga.get("referencia", "")

    cargo_type = carga.get("tipo_carga", "Contenedor")
    st.session_state["cargo_type"] = cargo_type

    if cargo_type == "Contenedor":
        detalle = carga.get("detalle", {}) or {}
        st.session_state["container_type"] = list(detalle.keys())
        for c_type, c_data in detalle.items():
            qty_key = f"qty_{c_type}"
            st.session_state[qty_key] = c_data.get("qty", 0)
            for idx, name in enumerate(c_data.get("names", [])):
                st.session_state[f"name_{c_type}_{idx}"] = name
    else:
        st.session_state["unidad_medida"] = carga.get("unidad_medida", "KG")
        st.session_state["cantidad_suelta"] = float(carga.get("cantidad_suelta", 0.0))

    # --- Ventas ---
    st.session_state["sales_blocks"] = reconstruir_sales_blocks(ventas)

    # --- Costos ---
    st.session_state["cost_surcharges"] = [
        {
            "concept": c.get("concepto", ""),
            "quantity": float(c.get("cantidad", 0.0)),
            "rate": float(c.get("tarifa", 0.0)),
            "total": float(c.get("monto", 0.0)),
            "currency": c.get("moneda", "USD"),
        }
        for c in costos
    ]
    if costos and any(c.get("comentarios") for c in costos):
        st.session_state["final_comments_cost"] = next(
            (c.get("comentarios") for c in costos if c.get("comentarios")), ""
        )
    else:
        st.session_state["final_comments_cost"] = ""

    return True


def reconstruir_sales_blocks(ventas_master_db):
    """
    Reconstruye los bloques de venta a partir de la estructura nueva:
    - ventas_master: info general
    - detalles: lista de recargos (ventas_detalle)
    """
    blocks = []
    for venta in ventas_master_db:
        block = {
            "id_venta_master": venta.get("id_venta_master"),  # para NC
            "client": venta.get("cliente", ""),
            "sales_surcharges": [],
            "comments": venta.get("comentarios", "")
        }
        for detalle in venta.get("detalles", []):
            block["sales_surcharges"].append({
                "concept": detalle.get("concepto", ""),
                "quantity": float(detalle.get("cantidad", 0)),
                "rate": float(detalle.get("tarifa", 0)),
                "total": float(detalle.get("monto", 0)),
                "currency": detalle.get("moneda", "USD")
            })
        blocks.append(block)
    return blocks


def prepare_venta_data(venta_info: dict) -> dict:
    """
    Prepara la estructura de una venta para PDF o exportación.
    """
    venta_data = venta_info.get("venta", {})
    carga_data = venta_info.get("carga", {})

    return {
        "no_solicitud": venta_info.get("no_solicitud", ""),
        "client": venta_data.get("cliente", ""),
        "id_venta_master": venta_data.get("id_venta_master", None),

        # Recargos
        "sales_surcharges": venta_data.get("sales_surcharges", []),
        "cost_surcharges": venta_info.get("cost_surcharges", []),

        # Información de la carga
        "bl_awb": carga_data.get("bl_awb", ""),
        "pol_aol": carga_data.get("pol_aol", ""),
        "pod_aod": carga_data.get("pod_aod", ""),
        "shipper": carga_data.get("shipper", ""),
        "consignee": carga_data.get("consignee", ""),
        "reference": carga_data.get("reference", ""),
        "cargo_type": carga_data.get("cargo_type", ""),
        "container_details": carga_data.get("container_details", {}),
        "unidad_medida": carga_data.get("unidad_medida", ""),
        "cantidad_suelta": carga_data.get("cantidad_suelta", 0),

        # Datos de cliente
        "customer_phone": venta_data.get("customer_phone", ""),
        "customer_address": venta_data.get("customer_address", ""),
        "customer_account": venta_data.get("customer_account", ""),
        "customer_nit": venta_data.get("customer_nit", ""),
        "customer_contact": venta_data.get("customer_contact", ""),
        "customer_email": venta_data.get("customer_email", ""),

        # Comentarios finales
        "comentarios": venta_info.get("comentarios", ""),
    }
