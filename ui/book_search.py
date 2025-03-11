import streamlit as st
import faiss
import json
from sentence_transformers import SentenceTransformer
import time

# 모델 로드 함수 (캐시 적용)
@st.cache_resource(ttl=3600)
def load_model():
    return SentenceTransformer("BM-K/KoSimCSE-roberta")

# FAISS 로드 함수
@st.cache_resource(ttl=3600)
def load_faiss():
    return faiss.read_index("./modeling/book_faiss_cosine_index.bin")

# 책 정보 로드 함수
@st.cache_resource(ttl=3600)
def load_books():
    with open("./data/All_books_with_summary.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 비슷한 책 찾는 함수
def find_similar_books(user_story, top_k=5):
    faiss_index = load_faiss()
    books_data = load_books()
    book_titles = [book["title"] for book in books_data]
    book_summaries = [book["summary"] for book in books_data]

    # 모델 로드 (캐시된 모델 사용)
    embedding_model = load_model()
    user_embedding = embedding_model.encode([user_story], convert_to_numpy=True)
    faiss.normalize_L2(user_embedding)

    distances, indices = faiss_index.search(user_embedding, top_k)

    recommended_books = [{
        "title": book_titles[indices[0][i]],
        "summary": book_summaries[indices[0][i]]
    } for i in range(top_k)]

    return recommended_books

# 책 개수 반환 함수
def get_books_count():
    try:
        books_data = load_books() 
        return len(books_data)
    except FileNotFoundError:
        return 0
    except json.JSONDecodeError:
        return 0

# 책 검색 실행 함수
def run_search_books():
    # 책의 개수를 가져와서 동적으로 마크다운에 반영

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        pass
    with col2:
        st.image("image/pose_souzou_woman.png", width=300)
    with col3:
        if st.button("👩🏻‍💻 개발과정 보러가기"):
            st.session_state.page = "page2"
            st.rerun()

    book_count = get_books_count()
    st.markdown(f"""
        <div style="position: relative; background-color: #fdfdfd; padding: 10px 25px 5px 65px; border-radius: 0px 10px; border: 1px solid #e5e5e5; box-shadow: 1px 2px 3px 1px rgba(0,0,0,.1);">
            <div style="position: absolute; top: -1px; left: 14px; width: 30px; height: 47px; background-color: #a7e7c4;">&nbsp;</div>
            <div style="position: absolute; top: 17px; left: 14px; width: 0; height: 0; border: 15px solid; border-color: transparent transparent #fdfdfd transparent;">&nbsp;</div>
            <h2 style="color: #333333; font-family: 'Georgia', Arial;">🔍 이 소설 뭐더라??</h2>
            <p style="color: #555555; font-size: 16px; font-family: 'Arial', sans-serif;">
                스토리는 어렴풋이 생각 나는데...<br>
                소설 제목이 기억나지 않으신다고요?<br><br>
                <strong>대략의 줄거리를 입력하면 그 내용과 비슷한 책을 찾아드립니다!</strong><br><br>
                <strong>네이버에서 제공되는 소설 데이터 중 줄거리가 제공된 소설과<br> 
                여러분의 피드백으로 추가된 소설 {book_count}권</strong>을 기반으로 검색되며,<br>
                소설의 엔딩보다는 <strong>시작 부분을 입력</strong>하시는 것이 더 정확한 검색 결과를 얻는 데 도움이 됩니다.
            </p>
            <p style="color: #777777; font-size: 14px; font-family: 'Arial', sans-serif; text-align: center;">
                📚 <span style="font-weight: bold;">책을 찾고 싶다면 스토리를 입력해보세요!</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if "book_index" not in st.session_state:
        st.session_state["book_index"] = 0

    if "books_not_found" not in st.session_state:
        st.session_state["books_not_found"] = []

    user_story = st.text_area("🔹 스토리를 입력하세요.", placeholder="한 고아소년이 마법사가 되는 소설")
    st.session_state['user_story'] = user_story

    # 버튼 클릭을 한 번만 가능하게 처리
    if "searching" not in st.session_state:
        st.session_state["searching"] = False

    if st.button("🔍 도서 찾기") and not st.session_state["searching"]:
        if not user_story.strip():
            st.warning("스토리를 입력해주세요.")
            return

        # 버튼 클릭 시 상태 업데이트
        st.session_state["searching"] = True

        # 로딩 표시
        with st.spinner("책을 찾는 중..."):
            faiss_results = find_similar_books(user_story, top_k=5)

            if faiss_results:
                st.session_state["books_not_found"] = faiss_results
                st.session_state["book_index"] = 0
                st.session_state["is_searched"] = True
                st.session_state.page = "page1"
            else:
                st.warning("검색된 책이 없습니다.")

        # 검색 후 버튼 상태 초기화
        st.session_state["searching"] = False
