import time
import requests
import streamlit as st
import toml
import urllib
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Google Drive 인증 함수
def authenticate_gdrive():
    """Google Drive 인증 함수."""
    # Streamlit secrets 로드 확인
    if "gdrive" not in st.secrets:
        st.error("⚠️ `secrets.toml`이 설정되지 않았습니다. Streamlit Secrets Manager에서 설정해 주세요.")
        return None

    creds_dict = {
        "type": "service_account",
        "project_id": "neon-bank-447604-s6",
        "private_key_id": st.secrets["gdrive"].get("private_key_id", ""),
        "private_key": st.secrets["gdrive"].get("private_key", "").replace("\\n", "\n"),
        "client_email": st.secrets["gdrive"].get("client_email", ""),
        "client_id": st.secrets["gdrive"].get("client_id", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": st.secrets["gdrive"].get("client_x509_cert_url", ""),
    }

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )

    gauth = GoogleAuth()
    gauth.credentials = creds
    drive = GoogleDrive(gauth)

    return drive

# 📌 네이버 API 키 로드 함수
def get_naver_api_keys():
    """secrets.toml에서 Naver API 키 가져오기."""
    config = toml.load('./.streamlit/secrets.toml')
    return config['NAVER_CLIENT_ID'], config['NAVER_CLIENT_SECRET']

# 📌 네이버 API를 사용하여 책 정보 가져오기
def get_book_info_from_naver(book_title):
    """네이버 API를 통해 책 정보를 가져오는 함수."""
    client_id, client_secret = get_naver_api_keys()
    url = "https://openapi.naver.com/v1/search/book.json"
    params = {'query': book_title, 'display': 1}
    headers = {'X-Naver-Client-Id': client_id, 'X-Naver-Client-Secret': client_secret}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['items']:
            book = data['items'][0]
            return {
                'title': book['title'],
                'author': book['author'],
                'publisher': book['publisher'],
                'image': book['image'],
                'description': book['description']
            }
    return None

# ✅ 피드백 저장 및 Google Drive 업로드 함수
def save_feedback():
    """피드백을 저장하고 Google Drive에 업로드하는 함수."""
    feedback_text = st.session_state.get("feedback_text", "").strip()
    if not feedback_text:
        st.warning("⚠️ 피드백을 입력해 주세요.")
        return

    user_story = st.session_state.get("user_story", "No Story Provided")

    # 로컬에 파일 저장 (임시 파일)
    file_name = "book_feedback.txt"
    local_path = os.path.join("/tmp", file_name)  # 배포 환경에서는 /tmp 사용
    with open(local_path, "a") as f:
        f.write(f"Story: {user_story}\n")
        f.write(f"Feedback: {feedback_text}\n")
        f.write("-" * 40 + "\n")

    # Google Drive에 업로드
    drive = authenticate_gdrive()
    folder_id = st.secrets["gdrive"]["folder_id"]  # Google Drive 폴더 ID

    if drive:
        # 기존 파일을 찾기 (파일명으로 검색)
        file_list = drive.ListFile({'q': f"title = '{file_name}' and '{folder_id}' in parents"}).GetList()

        if file_list:
            # 파일이 존재하면 다운로드 후 수정
            file_drive = file_list[0]
            file_drive.GetContentFile(local_path)  # 파일 다운로드
            with open(local_path, "a") as f:
                f.write(f"Story: {user_story}\n")
                f.write(f"Feedback: {feedback_text}\n")
                f.write("-" * 40 + "\n")

            # 파일 다시 업로드
            file_drive.SetContentFile(local_path)
            file_drive.Upload()
            st.success("✅ 피드백이 저장되었습니다! 의견 감사합니다.")
        else:
            # 파일이 없으면 새로 생성
            file_drive = drive.CreateFile({"title": file_name, "parents": [{"id": folder_id}]})
            file_drive.SetContentFile(local_path)
            file_drive.Upload()
            st.success("✅ 피드백이 저장되었습니다! 의견 감사합니다.")

        st.write(f"📂 [Google Drive에서 확인하기](https://drive.google.com/drive/folders/{folder_id})")

        # 상태 초기화
        st.session_state["feedback_saved"] = True
        st.session_state["feedback_text"] = ""
        st.session_state["book_index"] = 0
        st.session_state["books_displayed"] = []
        st.session_state.page = "book_search"

# 📌 UI 실행 함수
def run_1():
    """책 검색 및 피드백 저장 UI 처리 함수."""
    # 상태 초기화
    if "book_index" not in st.session_state:
        st.session_state["book_index"] = 0

    if "books_displayed" not in st.session_state:
        st.session_state["books_displayed"] = []

    if "books_not_found" not in st.session_state or len(st.session_state["books_not_found"]) == 0:
        st.error("🔍 검색할 소설이 없습니다.")
        return

    # 현재 책 정보 가져오기
    book_index = st.session_state["book_index"]
    book = st.session_state["books_not_found"][book_index]

    # 네이버 API를 사용하여 책 정보 가져오기
    book_info = get_book_info_from_naver(book['title'])

    if book_info:
        # 책 정보 중복 추가 방지
        if book_info not in st.session_state["books_displayed"]:
            st.session_state["books_displayed"].append(book_info)

        # 저장된 책 목록 출력
        for idx, displayed_book in enumerate(st.session_state["books_displayed"]):
            col1, col2 = st.columns([4, 2])
            with col1:
                st.subheader(f"📚 이 소설일까요? - 후보 {idx + 1}")
                st.subheader(f"📖 **{displayed_book['title']}**")
                st.write(f"✍️ 작가: {displayed_book['author']}")
                st.write(f"📌 출판사: {displayed_book['publisher']}")

            with col2:
                st.image(displayed_book['image'], caption=displayed_book['title'], width=200)

            st.write(f"📜 책 설명:\n{displayed_book['description']}")
            st.write("---")
    else:
        st.write(f"❌ '{book['title']}'에 대한 정보를 찾을 수 없습니다.")

    # ✅ "이 소설이 맞아요" 버튼
    if st.button("✅ 이 소설이 맞아요", key=f"book_{book_index}_yes"):
        st.success(f"🎉 '{book['title']}' 책을 찾았습니다!")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            pass
        with col2:
            st.image("image/book_hirameki_keihatsu_woman.png", width=300)
        with col3:
            pass
        st.balloons()
        st.session_state["book_index"] = 0  # 검색이 끝났으니 인덱스 초기화
        st.session_state["books_displayed"] = []  # 리스트 초기화
        st.session_state.page = "book_search"  # 페이지 전환
        time.sleep(3)
        st.rerun()

    # 피드백 저장
    if st.button("❌ 이 소설이 아니에요", key=f"book_{book_index}_no"):
        if st.session_state["book_index"] < len(st.session_state["books_not_found"]) - 1:
            st.session_state["book_index"] += 1  # 다음 책으로 이동
        else:
            st.write("❌ 더 이상 후보가 없습니다. 구글에서 검색해볼까요?")
            user_story = st.session_state["user_story"].replace("\n", " ") + "라는 줄거리의 소설은"
            encoded_user_story = urllib.parse.quote(user_story)
            st.markdown(f"[구글에서 줄거리를 검색](https://www.google.com/search?q={encoded_user_story})")

            # 피드백 텍스트 박스
            if "feedback_saved" not in st.session_state:
                st.session_state["feedback_saved"] = False  # 초기값 설정

            # 폼을 사용하여 피드백을 받음
            with st.form(key="feedback_form"):
                st.text_area("이 소설이었을 것 같아요 (의견을 남겨주세요)", placeholder="책에 대한 의견을 남겨주세요...", key="feedback_text")
                st.form_submit_button("피드백 저장", on_click=save_feedback)  # on_click으로 함수 지정
