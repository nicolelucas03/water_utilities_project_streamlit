import streamlit as st
st.title("Streamlit App")
st.write("Hello, world!")

# Sidebar selections
add_selectbox = st.sidebar.selectbox(
    "Select Country", 
    ("Cameroon", "Lesotho", "Malawi", "Uganda")
)

with st.sidebar: 
    add_radio = st.radio(
        "Choosing a shipping method", 
        ("Standard", "Express")
    )
