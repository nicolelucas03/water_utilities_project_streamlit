from streamlit_extras.stylable_container import stylable_container

#credits to https://github.com/ObservedObserver/streamlit-shadcn-ui/blob/main/pages/Card.py 
def card_container(key=None):
    return stylable_container(key=key, css_styles=[
    """
    {
        --tw-ring-offset-shadow: 0 0 #0000;
        --tw-ring-shadow: 0 0 #0000;
        --tw-shadow: 0 1px 3px 0 rgba(0,0,0,.1),0 1px 2px -1px rgba(0,0,0,.1);
        border-radius: 8px; /* Rounded corners */
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); /* Shadow effect */
        transition: 0.3s; /* Smooth transition for hover effect */
        padding: 1.5em; /* Inner spacing */
        border: 1px solid #5681d0;
        box-sizing: border-box;
        overflow: hidden; /* Enable scroll on small screens */
        box-shadow: var(--tw-ring-offset-shadow,0 0 #0000),var(--tw-ring-shadow,0 0 #0000),var(--tw-shadow);
        background-color: #1a1a3d; 
        color: white; 
    }
    """,
    """
        > div:not(:first-child) {
            width: 100%;
            min-width: 1px;
            overflow: hidden;
            color: #1e3a8a; /* Dark blue text for nested elements */
        }
        """,
        """
        > div:first-child {
            display: none;
        }
        """,
        """
        > div:not(:first-child) > iframe {
            display: inline-block;
            width: 100%; /* Adjusting for padding */
            min-width: 1px;
            border: none;
            overflow: hidden;
        }
        """,
        """
        > div:not(:first-child) canvas {
            display: inline-block;
            width: 100% !important; /* Adjusting for padding */
            min-width: 1px;
            border: none;
            overflow: hidden;
        }
        """
    ])