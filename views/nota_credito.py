import streamlit as st
import pandas as pd
from database.crud.operaciones import (
    obtener_ventas_por_solicitud,
    obtener_notas_credito_por_venta
)
from database.crud.nota_credito import insertar_nota_credito

def show():
    st.header("Registro de Notas Crédito")

    no_solicitud = st.text_input("Ingrese Número de Solicitud*", key="nc_no_solicitud")

    if no_solicitud:
        ventas = obtener_ventas_por_solicitud(no_solicitud)

        if not ventas:
            st.info("No hay ventas registradas para este número de solicitud.")
            return

        st.subheader("Ventas Asociadas")

        # Lista acumuladora para la tabla final
        notas_credito_global = []

        for v_idx, venta in enumerate(ventas):
            id_venta_master = venta["id_venta_master"]
            monto_venta = venta["monto_total"]
            moneda = venta["moneda"]
            cliente = venta["cliente"]

            notas = obtener_notas_credito_por_venta(id_venta_master)
            total_nc = sum(n["valor_nc"] for n in notas)
            open_balance = float(monto_venta) - float(total_nc)

            # Agregar estas notas a la lista global
            for n in notas:
                notas_credito_global.append({
                    "Venta #": id_venta_master,
                    "Cliente": cliente,
                    "Factura": n["no_factura"],
                    "Valor": n["valor_nc"],
                    "Razón": n.get("razon", "")
                })

            with st.expander(f"**Venta #{v_idx+1} - {cliente}**"):

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Notas Crédito registradas:**")
                    st.markdown(f"{len(notas)}")
                
                with col2:
                    st.markdown("**Total Original:**")
                    st.markdown(f"{monto_venta:.2f} {moneda}")
                
                with col3:
                    st.markdown("**Saldo Disponible:**")
                    st.markdown(f"{open_balance:.2f} {moneda}")

                col4, col5, col6, col7 = st.columns(4)

                with col4:
                    no_factura = st.text_input("Número de Factura*", key=f"factura_{id_venta_master}")

                with col5:
                    tipo_nc = st.selectbox("Tipo de Nota Crédito", ["Valor Parcial", "Valor Total"], key=f"tipo_nc_{id_venta_master}")

                with col6:
                    if tipo_nc == "Valor Total":
                        valor_nc = float(open_balance)
                        st.number_input(
                            "Valor de la Nota Crédito*",
                            value=valor_nc,
                            disabled=True,
                            key=f"valor_nc_{id_venta_master}"
                        )
                    else:
                        valor_nc = st.number_input(
                            "Valor de la Nota Crédito*",
                            min_value=0.0,
                            max_value=float(open_balance),
                            step=0.01,
                            key=f"valor_nc_{id_venta_master}"
                        )
                with col7:
                    razones_opciones = [
                        "CAMBIOS DE VENTA - COMERCIAL O CUSTOMER",
                        "CLIENTE SOLICITA FACTURAR A OTRA RAZON SOCIAL",
                        "NO ENTRO EN EL CIERRE DE MES",
                        "FALTO PO"
                    ]
                    razon = st.selectbox("Razón de la Nota Crédito*", razones_opciones, key=f"razon_nc_{id_venta_master}")

                if st.button("💾 Guardar Nota Crédito", key=f"guardar_nc_{id_venta_master}"):
                    if not no_factura:
                        st.warning("⚠️ Debes ingresar el número de factura.")
                    elif valor_nc <= 0:
                        st.warning("⚠️ El valor debe ser mayor a cero.")
                    elif valor_nc > open_balance:
                        st.warning("⚠️ El valor excede el saldo disponible.")
                    else:
                        insertar_nota_credito(
                            no_solicitud=no_solicitud,
                            no_factura=no_factura,
                            tipo_nc=tipo_nc,
                            valor_nc=valor_nc,
                            razon=razon,
                            id_venta_master=id_venta_master
                        )
                        st.success("✅ Nota crédito registrada correctamente.")
                        st.rerun()

        # Mostrar tabla de todas las notas crédito registradas
        if notas_credito_global:
            st.markdown("### 📋 Notas Crédito Registradas")
            df_nc = pd.DataFrame(notas_credito_global)
            st.dataframe(df_nc, use_container_width=True)
        else:
            st.info("No hay notas crédito registradas para estas ventas.")
