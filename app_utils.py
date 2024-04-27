import streamlit as st


def get_user_confirmation(message, callbacks):
    st.session_state["confirmation_callback_confirmed"] = callbacks[0]
    st.session_state["confirmation_callback_not_confirmed"] = callbacks[1]
    st.session_state["confirmation_needed"] = True
    st.session_state["confirmation_message"] = message
    st.rerun()


def set_raw_llm_response(text):
    st.session_state["raw_llm_response"] = text
