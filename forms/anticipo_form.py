import streamlit as st
import math
import pytz
# from utils.helpers import *

colombia_timezone = pytz.timezone('America/Bogota')

def forms(clients_list):
    col1, col2 = st.columns(2)

    commercial_op = [" ","Pedro Luis Bruges", "Andrés Consuegra", "Ivan Zuluaga", "Sharon Zuñiga",
            "Johnny Farah", "Felipe Hoyos", "Jorge Sánchez",
            "Irina Paternina", "Stephanie Bruges"]

    with col1:
        commercial = st.selectbox("Select Sales Rep*", commercial_op, key="commercial")
    with col2:
        no_solicitud = st.text_input("Operation Number (M)*", key="no_solicitud")

    with st.expander("**Client Information**",expanded=True):
        client = st.selectbox("Select your Client*", [" "] + ["+ Add New"] + clients_list, key="client")

        new_client_saved = st.session_state.get("new_client_saved", False)

        if client == "+ Add New":
            st.write("### Add a New Client")
            new_client_name = st.text_input("Enter the client's name:", key="new_client_name")

            if st.button("Save Client"):
                if new_client_name:
                    if new_client_name not in st.session_state["clients_list"]:
                        st.session_state["clients_list"].append(new_client_name)
                        st.session_state["client"] = new_client_name
                        st.session_state["new_client_saved"] = True
                        st.success(f"✅ Client '{new_client_name}' saved!")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ Client '{new_client_name}' already exists in the list.")
                else:
                    st.error("⚠️ Please enter a valid client name.")

        col1, col2, col3 = st.columns(3)

        with col1:
            customer_name = st.text_input("Customer Name*", key="customer_name")
        with col2:
            customer_phone = st.text_input("Customer Phone", key="customer_phone")
        with col3:
            customer_email = st.text_input("Customer Email", key="customer_email")
    
    with st.expander("**Transport Information**", expanded=True):
        container_op = ["20' Dry Standard",
            "40' Dry Standard",
            "40' Dry High Cube",
            "Reefer 20'",
            "Reefer 40'",
            "Open Top 20'",
            "Open Top 40'",
            "Flat Rack 20'",
            "Flat Rack 40'",
            'LCL']

        container_type= st.multiselect("Select Container Type(s)*", container_op, key='container_type')
        col4, col5, col6 = st.columns(3)
        transp_op = ['Flete Internacional', 'Transporte Terrestre', 'Agenciamiento ']
        with col4:
            transport_type = st.multiselect("Select Service Type(s)*", transp_op, key="transport_type")
        with col5:
            operation_type = st.text_input("Operation Type*", key="operation_type")
        with col6:
            reference = st.text_input("Customer Reference", key="reference")

    with st.expander("**Surcharges**", expanded=True):

        if "additional_surcharges" not in st.session_state or not isinstance(st.session_state["additional_surcharges"], dict):
            st.session_state["additional_surcharges"] = {}

        def remove_surcharge(container, index):
            del st.session_state["additional_surcharges"][container][index]

        def add_surcharge(container):
            st.session_state["additional_surcharges"][container].append({"concept": "", "currency": "", "cost": 0.0})

        all_surcharges = []
        for cont in container_type:
            if cont not in st.session_state["additional_surcharges"]:
                st.session_state["additional_surcharges"][cont] = []

            all_surcharges.extend(st.session_state["additional_surcharges"][cont])

        currencies = {s["currency"] for s in all_surcharges if s["currency"]}

        need_trm = "USD" in currencies and "COP" in currencies

        if need_trm:
            trm = st.number_input("Enter TRM (USD to COP)*", min_value=0.0, step=0.01, key="trm")
        else:
            trm = None

        total = 0
        currency_total = "COP" if currencies == {"COP"} else "USD" if currencies == {"USD"} else "COP"

        for cont in container_type:
            st.write(f"**{cont}**")

            for i, surcharge in enumerate(st.session_state["additional_surcharges"][cont]):
                col1, col2, col3, col4 = st.columns([2.5, 1, 0.5, 0.5])

                with col1:
                    surcharge["concept"] = st.text_input(f"Concept*", surcharge["concept"], key=f'{cont}_concept_{i}')

                with col2:
                    surcharge["currency"] = st.selectbox(f"Currency*", ['USD', 'COP'], index=0 if surcharge["currency"] == "USD" else 1, key=f'{cont}_currency_{i}')

                with col3:
                    surcharge["cost"] = st.number_input(f"Cost*", min_value=0.0, step=0.01, value=surcharge["cost"], key=f'{cont}_cost_{i}')

                with col4:
                    st.write(" ")
                    st.write(" ")
                    st.button("❌", key=f'remove_{cont}_{i}', on_click=remove_surcharge, args=(cont, i))

                if surcharge["currency"] == "USD":
                    total += surcharge["cost"] * (trm if need_trm else 1)
                else:
                    total += surcharge["cost"]

            st.button(f"➕ Add Surcharges", key=f"add_{cont}", on_click=add_surcharge, args=(cont,))

        total_rounded = math.ceil(total * 100) / 100
        symbol = "$" if currency_total == "USD" else "$"
        suffix = "USD" if currency_total == "USD" else "COP"
        formatted_total = f"{symbol}{total_rounded:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" {suffix}"
        st.markdown(f"### **Total: {formatted_total}**")

    request_data = {
        "no_solicitud": no_solicitud,
        "commercial": commercial,
        "client": st.session_state.get("client", client),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "container_type": container_type,
        "transport_type": transport_type,
        "operation_type": operation_type,
        "reference": reference,
        "additional_surcharges": st.session_state["additional_surcharges"],
        "trm": trm,
        "total_cop_trm": formatted_total
    }

    return request_data