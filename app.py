import streamlit as st
from multiapp import MultiApp
import Surprise_Map


st.set_page_config(layout="wide")


apps = MultiApp()

# Add all your application here


apps.add_app("Surprise Map", Surprise_Map.app)


# The main app
apps.run()
