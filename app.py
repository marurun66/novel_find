# app.py
import streamlit as st
from ui.book_search import run_search_books
from ui.page1 import run_1
from ui.page2 import run_2

st.set_page_config(
    layout="centered",
    page_title="이 소설 뭐더라?",
    page_icon="📚",
)
def main():

    if 'page' not in st.session_state:
        st.session_state.page = 'book_search' 

    if st.session_state.page == 'book_search':
        st.empty()
        run_search_books()
    elif st.session_state.page == 'page1':
        st.empty()
        run_1()

    elif st.session_state.page == 'page2':
        st.empty()
        run_2()


if __name__ == "__main__":
    main()
