import streamlit as st
from llm_communication import query_llm
import re


def stylize(text):
    # Regular expression to find <JSON>...</JSON>
    json_pattern = re.compile(r"<JSON>(.*?)<JSON/>", re.DOTALL)
    cot_pattern = re.compile(r"<COT>(.*?)<COT/>", re.DOTALL)

    # Replace the pattern with a styled span
    styled_text = re.sub(
        json_pattern,
        r'<span style="color:green;">\1</span>',
        text,
    )
    styled_text = re.sub(
        cot_pattern,
        r'<span style="color:yellow;">\1<</span>',
        styled_text,
    )

    return styled_text


# Streamlit interface
st.title("My LLM Interface")

# Text input for the user prompt
user_input = st.text_input("Enter your query:")

# Button to send the query to the LLM
if st.button("Submit"):
    # Display the response from the LLM
    response = query_llm(user_input, cleanup=False)
    st.markdown(stylize(response), unsafe_allow_html=True)
    # st.write(response)
