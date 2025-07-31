import streamlit as st
from services.authentication import check_authentication
from collections import defaultdict

st.set_page_config(page_title="Insides Platform", layout="wide")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.image("resources/images/logo_trading.png", width=800)

check_authentication()

user = st.user.name

with st.sidebar:
    page = st.radio("Go to", ["Home",  "Solicitud de Anticipo", "Pre orden", "Nota Crédito"])

if page == "Solicitud de Anticipo":
    import views.solicitud_anticipo as payment 
    payment.show()

elif page == "Pre orden":
    import views.pre_orden as pre
    pre.show()

elif page == "Nota Crédito":
    import views.nota_credito as nt
    nt.show()