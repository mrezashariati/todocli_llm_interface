import streamlit as st
from llm_communication import student_llm, get_tasks_data, reset_todocli
import pandas as pd

# Initialize the session states
if "cleanup_intended" not in st.session_state:
    st.session_state["cleanup_intended"] = False

if "raw_llm_response" not in st.session_state:
    st.session_state["raw_llm_response"] = ""


def set_cleanup_intended():
    # Set the state to indicate the action is confirmed
    st.session_state["cleanup_intended"] = True


def perform_cleanup():
    # Perform the action
    st.session_state["cleanup_intended"] = False  # Reset confirmation flag
    reset_todocli()
    st.rerun()


# Streamlit interface
st.title("Khanom Shirzad, the task manager at your command 😊")

# Text input for the user prompt
user_input = st.text_input("What can I do for you?")

# Background
page_element = """
    <style>
    [data-testid="stAppViewContainer"]{
        background-image: url("https://cdn.wallpapersafari.com/88/75/cLUQqJ.jpg");
        background-size: cover;
    }
    </style>
"""

st.markdown(page_element, unsafe_allow_html=True)

# Tasks table
data = pd.read_json(get_tasks_data())
data = data.drop(columns=["sort_by"], errors="ignore")
cols = st.columns([1, 4, 1])
with cols[1]:
    st.dataframe(data, width=500)
    if st.button("Submit"):
        st.session_state["raw_llm_response"] = student_llm(user_input, cleanup=False)
        st.rerun()
    if st.button("Remove All Tasks"):
        set_cleanup_intended()
    if st.session_state["cleanup_intended"]:
        st.write("Are you sure you want to perform this action?")
        if st.button("Yes, I'm sure"):
            perform_cleanup()
        if st.button("No"):
            st.session_state["cleanup_intended"] = False
            st.rerun()

    st.text_area("Raw LLM Response", st.session_state["raw_llm_response"], height=500)
