import streamlit as st
from forms.pre_orden_form import *
import pytz

def show():

    order_info = forms()

    # if st.button("Generar PDFs"):
    #     save_order_submission(order_info)
    #     register_new_client(order_info.get("client_finance"), st.session_state["clients_list_finance"])

    #     try:
    #         save_surcharges_orden(
    #             order_info.get("no_solicitud", ""),
    #             order_info.get("sales_surcharges", []),
    #             order_info.get("cost_surcharges", [])
    #         )
    #         st.success("✅ Recargos guardados en Google Sheets.")
    #     except Exception as e:
    #         st.error(f"❌ Error al guardar recargos: {e}")

    #     # Generar PDFs
    #     pdf_ventas = generate_archives(order_info, "ventas")
    #     pdf_costos = generate_archives(order_info, "costos")

    #     st.session_state["pdf_paths"] = (pdf_ventas, pdf_costos)
    #     st.success("✅ Archivos PDF creados exitosamente.")

    # if "pdf_paths" in st.session_state:
    #     pdf_ventas, pdf_costos = st.session_state["pdf_paths"]

    #     no_solicitud = order_info.get("no_solicitud", "")

    #     col1, col2 = st.columns(2)

    #     with col1:
    #         with open(pdf_ventas, "rb") as f:
    #             st.download_button(
    #                 label="Descargar Orden de Venta",
    #                 data=f,                       
    #                 file_name=f"ORDEN {no_solicitud}.pdf",
    #                 mime="application/pdf",
    #                 key="dl_ventas"
    #             )

    #     with col2:
    #         with open(pdf_costos, "rb") as f:
    #             st.download_button(
    #                 label=f"Descargar Pre-orden Costo.pdf",
    #                 data=f,
    #                 file_name=f"COSTO {no_solicitud}.pdf",
    #                 mime="application/pdf",
    #                 key="dl_costos"
    #             )
