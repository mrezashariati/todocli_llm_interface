import streamlit as st
from llm_communication import student_llm, get_tasks_data, reset_todocli
import pandas as pd

# Initialize the session states
if "cleanup_intended" not in st.session_state:
    st.session_state["cleanup_intended"] = False

if "raw_llm_response" not in st.session_state:
    st.session_state["raw_llm_response"] = ""

if "confirmation_needed" not in st.session_state:
    st.session_state["confirmation_needed"] = False

if "confirmation_message" not in st.session_state:
    st.session_state["confirmation_message"] = ""

if "confirmation_callback_confirmed" not in st.session_state:
    st.session_state["confirmation_callback_confirmed"] = None

if "confirmation_callback_not_confirmed" not in st.session_state:
    st.session_state["confirmation_callback_not_confirmed"] = None


def set_cleanup_intended():
    # Set the state to indicate the action is confirmed
    st.session_state["cleanup_intended"] = True


def perform_cleanup():
    # Perform the action
    st.session_state["cleanup_intended"] = False  # Reset confirmation flag
    reset_todocli()


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

    # Request Submission
    if st.button("Submit"):
        student_llm(user_input, cleanup=False)
        st.rerun()

    # Confirmation
    if st.session_state["confirmation_needed"]:
        st.write(st.session_state["confirmation_message"])
        st.session_state["confirmation_needed"] = False
        st.session_state["confirmation_message"] = ""
        st.button(
            "Yes, looks good!",
            on_click=st.session_state["confirmation_callback_confirmed"],
        )
        st.button(
            "No, stop that!",
            on_click=st.session_state["confirmation_callback_not_confirmed"],
        )

    # Tasks Deletion
    st.button("Remove All Tasks", on_click=set_cleanup_intended)
    if st.session_state["cleanup_intended"]:
        st.write("Are you sure you want to perform this action?")
        st.button("Yes, I'm sure", on_click=perform_cleanup)
        if st.button("No"):
            st.session_state["cleanup_intended"] = False
            st.rerun()

    # # Log Display
    # if st.session_state["raw_llm_response"]:
    #     st.text_area(
    #         "Raw LLM Response", st.session_state["raw_llm_response"], height=500
    #     )
