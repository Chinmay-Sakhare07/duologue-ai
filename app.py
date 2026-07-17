import streamlit as st
from groq import Groq

st.set_page_config(page_title="Duologue AI")

st.title("Duologue AI")
st.write("Turn any article, PDF, or topic into a two-host podcast conversation.")

if st.button("Test Groq connection"):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Say hello in one short sentence."}
        ],
    )
    st.success(response.choices[0].message.content)