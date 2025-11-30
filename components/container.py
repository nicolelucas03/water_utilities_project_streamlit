from streamlit_extras.stylable_container import stylable_container

def card_container(key=None):
    return stylable_container(
        key=key,
        css_styles=[
            """
            {
                border-radius: 8px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                transition: 0.3s;
                padding: 1.5em;
                border: 1px solid #5681d0;
                box-sizing: border-box;
                overflow: hidden;
                background-color: #1a1a3d; 
                color: #f8f8f2; 
                font-family: 'Poppins', sans-serif !important;
            }

            /* Force all nested text to white and correct font */
            * {
                color: #f8f8f2 !important;
                font-family: 'Poppins', sans-serif !important;
            }
            """
        ]
    )
