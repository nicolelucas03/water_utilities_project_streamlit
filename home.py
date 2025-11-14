import streamlit as st
st.title("Streamlit App")
st.write("Hello, world!")

add_selectbox = st.sidebar.selectbox(
    "Select Country", 
    ("CountryA", "CountryB", "CountryC")
)

with st.sidebar: 
    add_radio = st.radio(
        "Choosing a shipping method", 
        ("Standard", "Express")
    )