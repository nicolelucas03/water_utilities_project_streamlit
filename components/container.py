from streamlit_extras.stylable_container import stylable_container

#credits to https://github.com/ObservedObserver/streamlit-shadcn-ui/blob/main/pages/Card.py 
def card_container(key=None):
    return stylable_container(key=key, css_styles=[
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
    """,
    """
    > div:not(:first-child) {
        width: 100%;
        min-width: 1px;
        overflow: hidden;
        color: #f8f8f2;  /* Changed from dark blue */
        font-family: 'Poppins', sans-serif !important;
    }
    """, 
    # """
    # > div:first-child {
    #     display: none;
    # }
    # """,
    """
    > div:not(:first-child) > iframe {
        display: inline-block;
        width: 100%;
        min-width: 1px;
        border: none;
        overflow: hidden;
    }
    """,
    """
    > div:not(:first-child) canvas {
        display: inline-block;
        width: 100% !important;
        min-width: 1px;
        border: none;
        overflow: hidden;
    }
    """
    ])
