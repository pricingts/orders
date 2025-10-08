import streamlit as st
import pandas as pd
from database.crud.clientes import obtener_clientes, insertar_cliente
from database.crud.operaciones import guardar_operacion_completa
from ui.helpers import cargar_operacion_en_formulario
from services.pdf_generator.generate_preorden import generate_archives
from services.sheets_writer import save_order_submission

def forms():
    st.subheader("Facturas")

    if "client_new" in st.session_state:
        st.session_state["client"] = st.session_state.pop("client_new")

    clientes_db = obtener_clientes()
    clients_list = [c["cliente"] for c in clientes_db]
    client_lookup = {c["cliente"]: c for c in clientes_db}

    col1, col2 = st.columns(2)

    commercial_op = [" ","Pedro Luis Bruges", "Andrés Consuegra", "Ivan Zuluaga", "Sharon Zuñiga",
            "Johnny Farah", "Felipe Hoyos", "Jorge Sánchez",
            "Irina Paternina", "Stephanie Bruges"]
    
    paises = ["Colombia", "Estados Unidos", "Ecuador", "Mexico", "Panama", "Chile"]

    with col1:
        no_solicitud = st.text_input("Número del Caso (M)*", key="no_solicitud")

    if st.session_state.get("no_solicitud") and st.button("🔄 Cargar Datos"):
            cargado = cargar_operacion_en_formulario(no_solicitud)
            st.session_state["form_visible"] = True
            if cargado:
                st.session_state["form_loaded"] = True
                st.success(f"Datos de la operación {no_solicitud} cargados correctamente.")
                st.rerun()
            else:
                st.warning(f"No se encontró información para el caso {no_solicitud}.")

    if st.session_state.get("form_visible"):
        with col2:
            commercial = st.selectbox("Comercial*", commercial_op, key="commercial")

        with st.expander("**Información de la Carga**", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                bl_awb = st.text_input("BL/AWB*", key="bl_awb")
            with col2:
                shipper = st.text_input("Shipper*", key="shipper")
            with col3:
                consignee = st.text_input("Consignee*", key="consignee")

            col3, col4 = st.columns(2)
            with col3:
                pol_aol = st.text_input("POL/AOD*", key="pol_aol")
            with col4:
                pod_aod = st.text_input("POD/AOD*", key="pod_aod")

            reference = st.text_area("Referencia*", key="reference")

            col5, col6, col7 = st.columns(3)

            with col5:
                cargo_type = st.selectbox('Seleccione el tipo de carga', ['Contenedor', 'Carga suelta'], key='cargo_type')

            if cargo_type == "Contenedor":
                with col6:
                    container_op = [
                        "20' Dry Standard", "40' Dry Standard", "40' Dry High Cube", "Reefer 20'",
                        "Reefer 40'", "Open Top 20'", "Open Top 40'", "Flat Rack 20'", "Flat Rack 40'"
                    ]

                    selected_types = st.multiselect(
                        "Tipos de contenedor*", container_op, key="container_type"
                    )

                container_data = {}      

                if selected_types:
                    rows = (len(selected_types) + 1) // 2
                    for i in range(rows):
                        cols = st.columns(2)
                        for j in range(2):
                            idx = i * 2 + j
                            if idx < len(selected_types):
                                c_type = selected_types[idx]

                                qty_key   = f"qty_{c_type}"
                                base_name = f"name_{c_type}"  

                                with cols[j]:
                                    # ---------- Cantidad ----------
                                    qty = st.number_input(
                                        f"Cantidad para {c_type}*", min_value=0, step=1,
                                        key=qty_key
                                    )
                                    qty_int = int(qty)         

                                    # ---------- Nombres ----------
                                    names = []
                                    for n in range(qty_int):    
                                        name_key = f"{base_name}_{n}"
                                        name = st.text_input(
                                            f"Nombre {n+1} para {c_type}",
                                            key=name_key
                                        )
                                        names.append(name)

                                container_data[c_type] = {
                                    "qty": qty_int,
                                    "names": names              
                                }

                st.session_state["container_data"] = container_data

            else:
                with col6:
                    unidad_medida = st.selectbox("Unidad de Medida*", ['KG', 'CBM', 'KV'], key='unidad_medida')

                with col7:
                    cant_suelta = st.number_input('Cantidad*', min_value=0.0, step=0.1, key='cantidad_suelta')
            
            insurance = st.checkbox('Requiere Seguro', key='insurance')
            if insurance:
                col8, col9, col10 = st.columns(3)
                with col8:
                    valor_carga = st.number_input('Valor de la Carga', min_value=0.0, step=0.1, key='valor_carga')
                with col9:
                    porcentaje = st.number_input('Porcentaje (%)', min_value=0.0, step=0.1, key='porcentaje')
                with col10:
                    valor_seguro = valor_carga * (porcentaje / 100)
                    st.write("**Valor del seguro**")
                    st.write(valor_seguro)

        if "sales_blocks" not in st.session_state:
            st.session_state["sales_blocks"] = []

        def add_sales_block():
            st.session_state["sales_blocks"].append({
                "client": "",
                "sales_surcharges": [],
                "comments": ""
            })

        st.button("➕ Add Sale", key="add_sales_block", on_click=add_sales_block)

        for block_index, block in enumerate(st.session_state["sales_blocks"]):
            with st.expander(f"**Venta #{block_index + 1}**", expanded=True):

                # --- Actualizar la selección si se agregó un cliente nuevo ---
                if "client_new" in st.session_state:
                    if st.session_state["client_new"] not in clients_list:
                        clients_list.append(st.session_state["client_new"])
                    block["client"] = st.session_state.pop("client_new")
                else:
                    block["client"] = block.get("client", " ")

                # --- Selectbox principal ---
                block["client"] = st.selectbox(
                    "Selecciona el cliente*",
                    [" "] + ["+ Add New"] + clients_list,
                    index=([" "] + ["+ Add New"] + clients_list).index(block["client"])
                        if block["client"] in ([" "] + ["+ Add New"] + clients_list) else 0,
                    key=f"client_{block_index}"
                )

                # --- Cliente existente ---
                if block["client"] in client_lookup:
                    client_info = client_lookup[block["client"]]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.text_input("Teléfono", value=client_info.get("telefono_contacto", ""), key=f"customer_phone_{block_index}")
                    with col2:
                        st.text_input("Dirección", value=client_info.get("direccion", ""), key=f"customer_address_{block_index}")
                    with col3:
                        st.selectbox(
                            "País de Emisión",
                            paises,
                            index=paises.index(client_info.get("pais", "Colombia")) if client_info.get("pais", "Colombia") in paises else 0,
                            key=f"customer_account_{block_index}"
                        )
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.text_input("NIT", value=client_info.get("nit", ""), key=f"customer_nit_{block_index}")
                    with col5:
                        st.text_input("Contacto", key=f"customer_contact_{block_index}")
                    with col6:
                        st.text_input("Correo Electrónico", value=client_info.get("correo", ""), key=f"customer_email_{block_index}")

                # --- Opción para agregar un nuevo cliente ---
                elif block["client"] == "+ Add New":
                    st.markdown("### **Nuevo Cliente**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_cliente = st.text_input("Nombre del Cliente*", key=f"new_cliente_{block_index}")
                        new_telefono = st.text_input("Teléfono*", key=f"new_telefono_{block_index}")
                    with col2:
                        new_nit = st.text_input("NIT*", key=f"new_nit_{block_index}")
                        new_correo = st.text_input("Correo Electrónico*", key=f"new_correo_{block_index}")
                    with col3:
                        new_direccion = st.text_input("Dirección*", key=f"new_direccion_{block_index}")
                        new_pais = st.selectbox("País*", paises, key=f"new_pais_{block_index}")

                    if st.button("💾 Guardar Cliente", key=f"save_new_client_{block_index}"):
                        if new_cliente and new_nit and new_direccion and new_telefono and new_correo:
                            # Insertar en la base de datos
                            insertar_cliente(
                                cliente=new_cliente,
                                nit=new_nit,
                                direccion=new_direccion,
                                telefono_contacto=new_telefono,
                                correo=new_correo,
                                pais=new_pais
                            )
                            st.success(f"Cliente '{new_cliente}' agregado con éxito.")

                            # Guardar datos en session_state para PDF y siguiente render
                            st.session_state[f"customer_phone_{block_index}"] = new_telefono
                            st.session_state[f"customer_address_{block_index}"] = new_direccion
                            st.session_state[f"customer_account_{block_index}"] = new_pais
                            st.session_state[f"customer_nit_{block_index}"] = new_nit
                            st.session_state[f"customer_contact_{block_index}"] = ""
                            st.session_state[f"customer_email_{block_index}"] = new_correo

                            block["client"] = new_cliente 
                            st.session_state["client_new"] = new_cliente
                            st.rerun()
                        else:
                            st.warning("Por favor completa todos los campos obligatorios.")

                # --- Recargos ---
                if "sales_surcharges" not in block or not isinstance(block["sales_surcharges"], list):
                    block["sales_surcharges"] = []

                def add_block_surcharge(idx=block_index):
                    st.session_state["sales_blocks"][idx]["sales_surcharges"].append(
                        {"concept": "", "quantity": 0.0, "rate": 0.0, "total": 0.0, "currency": "USD"}
                    )

                for i, surcharge in enumerate(block["sales_surcharges"]):
                    col1, col2, col3, col4, col5, col6 = st.columns([2.5, 0.5, 0.8, 0.8, 0.7, 0.5])
                    with col1:
                        surcharge["concept"] = st.text_input(f"Concept*", value=surcharge["concept"], key=f'sale_concept_{block_index}_{i}')
                    with col2:
                        surcharge["quantity"] = st.number_input(f"Quantity*", value=surcharge.get("quantity", 0.0), min_value=0.0, step=0.01, key=f'sale_quantity_{block_index}_{i}')
                    with col3:
                        surcharge["rate"] = st.number_input(f"Rate*", value=surcharge.get("rate", 0.0), min_value=0.0, step=0.01, key=f'sale_rate_{block_index}_{i}')
                    with col4:
                        computed_total = surcharge["rate"] * surcharge["quantity"]
                        surcharge["total"] = computed_total
                        st.markdown(f"**Total**")
                        st.markdown(f"{computed_total:,.2f} {surcharge['currency']}")
                    with col5:
                        surcharge["currency"] = st.selectbox(
                            f"Currency*", ['USD', 'COP', 'MXN'],
                            index=['USD', 'COP', 'MXN'].index(surcharge["currency"]),
                            key=f'sale_currency_{block_index}_{i}'
                        )
                    with col6:
                        st.write(" ")
                        st.write(" ")
                        if st.button("❌", key=f'remove_sale_{block_index}_{i}'):
                            block["sales_surcharges"].pop(i)
                            st.rerun()

                # --- Botón para agregar recargo dentro de esta venta ---
                st.button("➕ Add Surcharge", key=f"add_sale_surcharge_{block_index}", on_click=lambda idx=block_index: add_block_surcharge(idx))

                comment_value = st.text_area(
                    "Comentarios de la Venta",
                    block.get("comments", ""),
                    key=f"final_comments_sale_{block_index}"
                )
                block["comments"] = comment_value 

                # --- Totales por moneda para este bloque ---
                sales_totals = {}
                for surcharge in block["sales_surcharges"]:
                    currency = surcharge["currency"]
                    value = surcharge.get("total", 0.0)
                    sales_totals[currency] = sales_totals.get(currency, 0.0) + value

                for currency, amount in sales_totals.items():
                    st.markdown(f"**Total {currency} (Venta #{block_index + 1})**: {amount:,.2f} {currency}")
                
                if st.button(f"📥 Descargar Venta #{block_index + 1}", key=f"download_sale_{block_index}"):
                    venta_info = {
                        "no_solicitud": st.session_state.get("no_solicitud", ""),
                        "comercial": st.session_state.get("commercial", ""),
                        "venta": {
                            "cliente": block["client"],
                            "customer_phone": st.session_state.get(f"customer_phone_{block_index}", ""),
                            "customer_address": st.session_state.get(f"customer_address_{block_index}", ""),
                            "customer_account": st.session_state.get(f"customer_account_{block_index}", ""),
                            "customer_nit": st.session_state.get(f"customer_nit_{block_index}", ""),
                            "customer_contact": st.session_state.get(f"customer_contact_{block_index}", ""),
                            "customer_email": st.session_state.get(f"customer_email_{block_index}", ""),
                            "sales_surcharges": block["sales_surcharges"]
                        },
                        "carga": {
                            "bl_awb": st.session_state.get("bl_awb", ""),
                            "pol_aol": st.session_state.get("pol_aol", ""),
                            "pod_aod": st.session_state.get("pod_aod", ""),
                            "shipper": st.session_state.get("shipper", ""),
                            "consignee": st.session_state.get("consignee", ""),
                            "reference": st.session_state.get("reference", ""),
                            "cargo_type": st.session_state.get("cargo_type", ""),
                            "container_details": st.session_state.get("container_data", {}),
                            "unidad_medida": st.session_state.get("unidad_medida", ""),
                            "cantidad_suelta": st.session_state.get("cantidad_suelta", 0),
                        },
                        "comentarios": block.get("comments", "") 
                    }
                    pdf_ventas = generate_archives(venta_info)

                    save_order_submission(venta_info, sheet_name="VENTA")

                    st.success(f"Se ha generado el archivo para Venta #{block_index + 1}.")
                    with open(pdf_ventas, "rb") as f:
                        st.download_button(
                            label="Descargar Orden de Venta",
                            data=f,                       
                            file_name=f"ORDEN_{no_solicitud}_{commercial}.pdf",
                            mime="application/pdf",
                            key="dl_ventas"
                        )

        total_sales_totals = {}
        for block in st.session_state.get("sales_blocks", []):
            for surcharge in block["sales_surcharges"]:
                currency = surcharge.get("currency", "USD")
                value = surcharge.get("total", 0.0)
                total_sales_totals[currency] = total_sales_totals.get(currency, 0.0) + value

        with st.expander("**Costos**", expanded=True):
            if "cost_surcharges" not in st.session_state or not isinstance(st.session_state["cost_surcharges"], list):
                st.session_state["cost_surcharges"] = []

            def remove_cost_surcharge(index):
                if 0 <= index < len(st.session_state["cost_surcharges"]):
                    st.session_state["cost_surcharges"].pop(index)

            def add_cost_surcharge():
                st.session_state["cost_surcharges"].append({"concept": "", "quantity": 0.0, "rate": 0.0 , "total": 0.0, "currency": "USD"})

            for i, surcharge in enumerate(st.session_state["cost_surcharges"]):

                col1, col2, col3, col4, col5, col6 = st.columns([2.5, 0.5, 0.8, 0.8, 0.7, 0.5])

                with col1:
                    surcharge["concept"] = st.text_input(f"Concept*", value=surcharge["concept"], key=f'cost_concept_{i}')

                with col2:
                    surcharge["quantity"] = st.number_input(f"Quantity*", value=surcharge["quantity"], min_value=0.0, step=0.01, key=f'cost_quantity_{i}')

                with col3:
                    surcharge["rate"] = st.number_input(f"Rate*", value=surcharge["rate"], min_value=0.0, step=0.01, key=f'cost_rate_{i}')

                with col4:
                    computed_total = surcharge["rate"] * surcharge["quantity"]
                    surcharge["total"] = computed_total
                    st.markdown(f"**Total**")
                    st.markdown(f"{computed_total:,.2f}")

                with col5:
                    surcharge["currency"] = st.selectbox(
                        f"Currency*", ['USD', 'COP', 'MXN'],
                        index=['USD', 'COP', 'MXN'].index(surcharge["currency"]),
                        key=f'cost_currency_{i}'
                    )

                with col6:
                    st.write(" ")
                    st.write(" ")
                    if st.button("❌", key=f'remove_cost_{i}'):
                        remove_cost_surcharge(i)
                        st.rerun()

            st.button("➕ Add Surcharge", key="add_cost_surcharge", on_click=add_cost_surcharge)

            final_comments = st.text_area("Comentarios de Costos", key="final_comments_cost")

            cost_totals = {}
            for surcharge in st.session_state["cost_surcharges"]:
                currency = surcharge["currency"]
                value = surcharge.get("total", 0.0)
                cost_totals[currency] = cost_totals.get(currency, 0.0) + value

            for currency, amount in cost_totals.items():
                st.markdown(f"**Total {currency}**: {amount:,.2f} {currency}")
        
            if st.button("📥 Descargar Costos", key="download_costos"):
                costos_info = {
                    "no_solicitud": st.session_state.get("no_solicitud", ""),
                    "comercial": st.session_state.get("commercial", ""),
                    "carga": {
                        "bl_awb": st.session_state.get("bl_awb", ""),
                        "pol_aol": st.session_state.get("pol_aol", ""),
                        "pod_aod": st.session_state.get("pod_aod", ""),
                        "shipper": st.session_state.get("shipper", ""),
                        "consignee": st.session_state.get("consignee", ""),
                        "reference": st.session_state.get("reference", ""),
                        "cargo_type": st.session_state.get("cargo_type", ""),
                        "container_details": st.session_state.get("container_data", {}),
                        "unidad_medida": st.session_state.get("unidad_medida", ""),
                        "cantidad_suelta": st.session_state.get("cantidad_suelta", 0),
                    },
                    "cost_surcharges": st.session_state.get("cost_surcharges", []),
                    "comentarios": st.session_state.get("final_comments_cost", ""),

                }

                pdf_costos = generate_archives(costos_info, variant="costos")

                save_order_submission(costos_info, sheet_name="COSTO")

                st.success("Se ha generado el archivo de Costos.")
                with open(pdf_costos, "rb") as f:
                    st.download_button(
                        label="Descargar Orden de Costos",
                        data=f,
                        file_name=f"COSTOS_{st.session_state.get('no_solicitud', '')}_{commercial}.pdf",
                        mime="application/pdf",
                        key="dl_costos"
                    )

        # --- Profit Global ---
        profit_totals = {}
        all_currencies = set(total_sales_totals) | set(cost_totals)
        for currency in all_currencies:
            sales_amount = total_sales_totals.get(currency, 0.0)
            cost_amount = cost_totals.get(currency, 0.0)
            profit_totals[currency] = sales_amount - cost_amount

        st.markdown("### **Profit de la Operación:**")
        for currency, amount in profit_totals.items():
            st.markdown(f"**Profit {currency}**: {amount:,.2f} {currency}")

        col1, col2 = st.columns(2)

        with col1:

            if st.button("💾 Guardar Orden"):
                operacion_data = {
                    "no_solicitud": no_solicitud,
                    "comercial": commercial
                }

                carga_data = {
                    "bl_awb": bl_awb,
                    "tipo_carga": cargo_type,
                    "pol_aol": pol_aol,
                    "pod_aod": pod_aod,
                    "shipper": shipper,
                    "consignee": consignee,
                    "detalle": container_data if cargo_type == "Contenedor" else None,
                    "unidad_medida": unidad_medida if cargo_type != "Contenedor" else None,
                    "cantidad_suelta": cant_suelta if cargo_type != "Contenedor" else None,
                    "referencia": reference
                }

                # --- Nuevo armado de ventas_data ---
                ventas_data = []
                for block in st.session_state.get("sales_blocks", []):
                    venta_master = {
                        "cliente": block["client"],
                        "moneda": block["sales_surcharges"][0]["currency"] if block["sales_surcharges"] else "USD",
                        "comentarios": block.get("comments", ""),
                        "detalles": []
                    }
                    for surcharge in block["sales_surcharges"]:
                        venta_master["detalles"].append({
                            "concepto": surcharge["concept"],
                            "cantidad": surcharge["quantity"],
                            "tarifa": surcharge["rate"],
                            "monto": surcharge["total"],
                            "moneda": surcharge["currency"]
                        })
                    ventas_data.append(venta_master)

                costos_data = [
                    {
                        "concepto": c["concept"],
                        "cantidad": c["quantity"],
                        "tarifa": c["rate"],
                        "monto": c["total"],
                        "moneda": c["currency"],
                        "comentarios": st.session_state.get("final_comments_cost", "")
                    }
                    for c in st.session_state.get("cost_surcharges", [])
                ]

                guardar_operacion_completa(operacion_data, carga_data, ventas_data, costos_data)
                st.success("✅ Orden guardada con éxito.")
            
            with col2:
                if st.button("🧹 Limpiar Formulario"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
