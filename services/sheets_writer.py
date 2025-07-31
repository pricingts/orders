import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import streamlit as st
from datetime import datetime
import pytz
import streamlit as st

credentials = Credentials.from_service_account_info(
    st.secrets["google_sheets_credentials"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
)


client_gcp = gspread.authorize(credentials)
sheets_service = build("sheets", "v4", credentials=credentials)
SPREADSHEET_ID = st.secrets["general"]["time_sheet_id"]
ORDEN_ID = st.secrets["general"]["orden_sheet"]
colombia_timezone = pytz.timezone('America/Bogota')

def get_or_create_worksheet(sheet_name: str, headers: list = None):
    try:
        sheet = client_gcp.open_by_key(SPREADSHEET_ID)
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="30")
            if headers:
                worksheet.append_row(headers)
            st.warning(f"Worksheet '{sheet_name}' was created.")
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("No se encontró la hoja de cálculo.")
        return None

def get_or_create_worksheet_orden(sheet_name: str, headers: list = None):
    try:
        sheet = client_gcp.open_by_key(ORDEN_ID)
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="30")
            if headers:
                worksheet.append_row(headers)
            st.warning(f"Worksheet '{sheet_name}' was created.")
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("No se encontró la hoja de cálculo.")
        return None

def save_anticipo_submission(data: dict):
    SHEET_NAME = "SOLICITUD DE ANTICIPO"
    headers = [
        "Comercial", "Fecha", "Cliente", "Nombre Cliente", "Teléfono Cliente", "Email Cliente", "Contenedores", 
        "Tipo Servicio", "Tipo Operación", "Referencia", "Recargos", "Total USD", "Total COP", "TRM", "Total COP TRM"
    ]

    worksheet = get_or_create_worksheet(SHEET_NAME, headers)
    if not worksheet:
        return

    try:
        # Extraer campos
        commercial = data["commercial"]
        client = data["client"]
        customer_name = data["customer_name"]
        customer_phone = data["customer_phone"]
        customer_email = data["customer_email"]
        operation_type = data["operation_type"]
        reference = data["reference"]
        trm = data["trm"]
        total_cop_trm = data["total_cop_trm"]

        # Contenedores y servicios
        containers = '\n'.join(
            '\n'.join(x) if isinstance(x, list) else x
            for x in data['container_type']
        )
        services = '\n'.join(
            '\n'.join(x) if isinstance(x, list) else x
            for x in data['transport_type']
        )

        # Recargos
        usd_total = 0.0
        cop_total = 0.0
        surcharge_lines = []
        for container_type, surcharges in data["additional_surcharges"].items():
            for surcharge in surcharges:
                cost = surcharge['cost']
                currency = surcharge['currency']
                concept = surcharge['concept']
                surcharge_lines.append(f"{container_type} - {concept}: ${cost:.2f} {currency}")
                if currency == "USD":
                    usd_total += cost
                elif currency == "COP":
                    cop_total += cost

        surcharge_str = '\n'.join(surcharge_lines)

        # Timestamp
        end_time = datetime.now(pytz.utc).astimezone(colombia_timezone)
        timestamp = end_time.strftime('%Y-%m-%d %H:%M:%S')

        # Escribir fila
        row = [
            commercial, timestamp, client, customer_name, customer_phone, customer_email, containers,
            services, operation_type, reference, surcharge_str, usd_total, cop_total, trm, total_cop_trm
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        st.success("Datos de solicitud de anticipo guardados correctamente.")
    except Exception as e:
        st.error(f"Error guardando datos en hoja de anticipo: {e}")

def register_new_client(client_name, clients_list):
    from ui.helpers import load_clients
    if not client_name: return

    client_normalized = client_name.strip().lower()
    normalized_existing = [c.strip().lower() for c in clients_list]

    if client_normalized not in normalized_existing:
        sheet = client_gcp.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet("clientes")
        worksheet.append_row([client_name])
        st.session_state["clients_list"].append(client_name)
        st.session_state["client"] = None
        load_clients.clear()
        st.rerun()


def save_order_submission(order_info: dict, sheet_name: str):
    headers = [
        "Comercial", "Fecha", "No Solicitud", "Datos Cliente",
        "BL/AWB", "Shipper", "Consignee", "Ruta (POL -> POD)", "Referencia",
        "Tipo Carga", "Detalles de la Carga",
        "Recargos", "Totales", "Comentarios Finales"
    ]

    worksheet = get_or_create_worksheet_orden(sheet_name, headers)
    if not worksheet:
        return

    try:
        # --- Comercial y número de solicitud ---
        commercial = order_info.get("commercial") or order_info.get("comercial", "")
        no_solicitud = order_info.get("no_solicitud", "")

        # --- Datos del cliente (dentro de venta) ---
        venta_data = order_info.get("venta", {})
        datos_cliente = (
            f"Nombre: {venta_data.get('cliente', '')}\n"
            f"Teléfono: {venta_data.get('customer_phone', '')}\n"
            f"Dirección: {venta_data.get('customer_address', '')}\n"
            f"Cuenta: {venta_data.get('customer_account', '')}\n"
            f"NIT: {venta_data.get('customer_nit', '')}\n"
            f"Contacto: {venta_data.get('customer_contact', '')}\n"
            f"Email: {venta_data.get('customer_email', '')}\n"
        )

        # --- Datos de la carga ---
        carga = order_info.get("carga", {})
        bl_awb = carga.get("bl_awb", "")
        shipper = carga.get("shipper", "")
        consignee = carga.get("consignee", "")
        ruta = f"{carga.get('pol_aol', '')} -> {carga.get('pod_aod', '')}"
        reference = carga.get("reference", "")
        cargo_type = carga.get("cargo_type", "")
        container_details = carga.get("container_details", {})
        unidad_medida = carga.get("unidad_medida", "")
        cantidad_suelta = carga.get("cantidad_suelta", "")

        if container_details:
            carga_lines = []
            for c_type, details in container_details.items():
                for name in details.get("names", []):
                    carga_lines.append(f"{c_type}: {name}")
            carga_str = '\n'.join(carga_lines)
        else:
            carga_str = f"{cantidad_suelta} {unidad_medida}"

        # --- Recargos ---
        sales_surcharges = venta_data.get("sales_surcharges", [])
        cost_surcharges = order_info.get("cost_surcharges", [])

        surcharge_lines = []
        recargos = sales_surcharges if sheet_name.upper() == "VENTA" else cost_surcharges
        for s in recargos:
            total = s.get("total", 0.0)
            currency = s.get("currency", "")
            surcharge_lines.append(
                f"{s.get('concept', '')}: {s.get('quantity', 0)} × {s.get('rate', 0)} = {total:.2f} {currency}"
            )
        surcharge_str = '\n'.join(surcharge_lines)

        # --- Totales ---
        if sheet_name.upper() == "VENTA":
            totals_by_currency = {}
            for s in sales_surcharges:
                currency = s.get("currency", "USD")
                totals_by_currency[currency] = totals_by_currency.get(currency, 0.0) + s.get("total", 0.0)
            
            total_str = "\n".join([f"Total Venta {currency}: {amount:.2f} {currency}" 
                                for currency, amount in totals_by_currency.items()])
        else:
            totals_by_currency = {}
            for s in cost_surcharges:
                currency = s.get("currency", "USD")
                totals_by_currency[currency] = totals_by_currency.get(currency, 0.0) + s.get("total", 0.0)
            
            total_str = "\n".join([f"Total Costo {currency}: {amount:.2f} {currency}" 
                                for currency, amount in totals_by_currency.items()])

        # --- Comentarios finales ---
        comentarios = order_info.get("comentarios", "")

        # --- Timestamp ---
        timestamp = datetime.now(pytz.utc).astimezone(colombia_timezone).strftime('%Y-%m-%d %H:%M:%S')

        # --- Fila final ---
        row = [
            commercial, timestamp, no_solicitud, datos_cliente,
            bl_awb, shipper, consignee, ruta, reference,
            cargo_type, carga_str,
            surcharge_str, total_str,
            comentarios
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")

    except Exception as e:
        st.error(f"Error guardando datos en hoja {sheet_name}: {e}")

def get_or_create_worksheet_nota_credito():
    headers = [
        "ID Nota",
        "Número Caso (M)",
        "Número Factura",
        "Tipo Nota",
        "Valor",
        "Razón",
        "Fecha Creación"
    ]
    return get_or_create_worksheet_orden("NOTA CREDITO", headers)


def save_nota_credito(nota_info: dict):
    """
    Guarda una nota de crédito en la hoja NOTA CREDITO.
    """
    ws = get_or_create_worksheet_nota_credito()
    if not ws:
        return

    colombia_timezone = pytz.timezone("America/Bogota")
    fecha_creacion = datetime.now(pytz.utc).astimezone(colombia_timezone).strftime("%Y-%m-%d %H:%M:%S")

    row = [
        nota_info.get("id_nc", ""),
        nota_info.get("no_solicitud", ""),
        nota_info.get("no_factura", ""),
        nota_info.get("tipo_nc", ""),
        nota_info.get("valor_nc", ""),
        nota_info.get("razon", ""),  # Nuevo campo Razón
        fecha_creacion
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")


def delete_nota_credito_sheet(id_nc: int):
    """
    Elimina una nota de crédito de la hoja NOTA CREDITO según el ID.
    """
    ws = get_or_create_worksheet_nota_credito()
    if not ws:
        return

    all_records = ws.get_all_records()
    for idx, record in enumerate(all_records, start=2):  # start=2 porque fila 1 = encabezados
        if str(record.get("ID Nota")) == str(id_nc):
            ws.delete_rows(idx)
            break


