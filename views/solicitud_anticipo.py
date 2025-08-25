import streamlit as st
from datetime import datetime
import pytz
from services.pdf_generator.generate_anticipo import generate_pdf
from ui.helpers import *
from services.sheets_writer import save_anticipo_submission, register_new_client
from forms.anticipo_form import forms

colombia_timezone = pytz.timezone('America/Bogota')

def show():

    colombia_timezone = pytz.timezone('America/Bogota')

    if "client" not in st.session_state:
        st.session_state["client"] = None

    if "clients_list" not in st.session_state:
        try:
            st.session_state["clients_list"] = load_clients()
        except Exception as e:
            st.error(f"Error al cargar la lista de clientes: {e}")
            st.session_state["clients_list"] = []

    if "start_time" not in st.session_state or st.session_state["start_time"] is None:
        st.session_state["start_time"] = datetime.now(colombia_timezone)

    clients_list = st.session_state["clients_list"]
    start_time = st.session_state["start_time"]

    request_data = forms(clients_list)

    if st.button('Send Information'):

        save_anticipo_submission(request_data)

        st.success("Information saved successfully!")

        register_new_client(request_data.get("client"), st.session_state["clients_list"])

        pdf_filename = generate_pdf(request_data)

        with open(pdf_filename, "rb") as f:
            pdf_bytes = f.read()

        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name="Solicitud de Anticipo.pdf",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )