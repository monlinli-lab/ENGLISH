import base64
import json
import random
import time
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(
    page_title="Frieren Spellbook",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MOE_VOCAB_BASE = {
    "動物與昆蟲": ["butterfly", "elephant", "dolphin", "mosquito", "squirrel", "dinosaur", "giraffe", "kangaroo", "penguin", "rabbit"],
    "食物與餐飲": ["hamburger", "sandwich", "spaghetti", "breakfast", "vegetable", "chocolate", "delicious", "restaurant", "strawberry", "cabbage"],
    "情緒與性格": ["confident", "generous", "impatient", "nervous", "cheerful", "frightened", "embarrassed", "energetic", "friendly", "selfish"],
    "動作與行為": ["celebrate", "describe", "experience", "imagine", "practice", "remember", "understand", "whisper", "complain", "encourage"],
    "環境與自然": ["mountain", "waterfall", "environment", "temperature", "volcano", "weather", "sunshine", "rainbow", "ocean", "forest"],
    "生活與居家": ["furniture", "refrigerator", "microwave", "blanket", "apartment", "balcony", "neighborhood", "curtain", "flashlight", "toothbrush"],
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at 50% 20%, rgba(120,70,10,0.18) 0%, rgba(2,6,23,1) 55%);
            color: #f8fafc;
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 5rem;
            max-width: 1200px;
        }
        div[data-testid="stHorizontalBlock"] > div {
            background: transparent;
        }
        .title-box {
            padding: 1.2rem 1.4rem;
            border-radius: 22px;
            background: rgba(15,23,42,0.82);
            border: 1px solid rgba(245,158,11,0.22);
            box-shadow: 0 10px 40px rgba(0,0,0,0.28);
            margin-bottom: 1rem;
        }
        .magic-card {
            background: rgba(15,23,42,0.72);
            border: 1px solid rgba(245,158,11,0.14);
            border-radius: 28px;
            padding: 1.4rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        }
        .word-chip {
            display: inline-block;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            background: rgba(245,158,11,0.12);
            border: 1px solid rgba(245,158,11,0.28);
            color: #fbbf24;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
        }
        .big-word {
            font-size: 2rem;
            font-weight: 800;
            color: #fef3c7;
            letter-spacing: 0.04em;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .section-title {
            color: #f59e0b;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }
        .history-box {
            background: rgba(15,23,42,0.58);
            border: 1px solid rgba(245,158,11,0.12);
            border-radius: 22px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }
        .error-box {
            background: rgba(127,29,29,0.22);
            border: 1px solid rgba(239,68,68,0.25);
            color: #fecaca;
            padding: 0.95rem 1rem;
            border-radius: 16px;
            margin-bottom: 1rem;
        }
        .small-note {
            color: #cbd5e1;
            opacity: 0.85;
            font-size: 0.92rem;
        }
        button[kind="primary"] {
            border-radius: 18px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session() -> None:
    defaults = {
        "result": None,
        "history": [],
        "current_category": random.choice(list(MOE_VOCAB_BASE.keys())),
        "suggested_words": [],
        "active_tab": "探求",
        "word_input": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not st.session_state["suggested_words"]:
        generate_random_five(st.session_state["current_category"])


def generate_random_five(category: str) -> None:
    pool = MOE_VOCAB_BASE[category][:]
    random.shuffle(pool)
    st.session_state["current_category"] = category
    st.session_state["suggested_words"] = pool[:5]


def pick_random_category() -> None:
    category = random.choice(list(MOE_VOCAB_BASE.keys()))
    generate_random_five(category)


def save_to_history(item: dict) -> None:
    history = st.session_state["history"]
    filtered = [h for h in history if h.get("word") != item.get("word")]
    st.session_state["history"] = [item] + filtered[:19]


def delete_from_history(word_to_delete: str) -> None:
    st.session_state["history"] = [h for h in st.session_state["history"] if h.get("word") != word_to_delete]


def get_api_key() -> str:
    return st.secrets.get("GOOGLE_API_KEY", "")


def fetch_with_retry(url: str, payload: dict, retries: int = 5, backoff: float = 1.0) -> dict:
    headers = {"Content-Type": "application/json"}
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            if response.ok:
                return response.json()
            last_error = RuntimeError(f"API error {response.status_code}: {response.text[:400]}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        if attempt < retries:
            time.sleep(backoff)
            backoff *= 2
    raise last_error if last_error else RuntimeError("Unknown API error")


def fetch_ai_content(target_word: str) -> None:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未設定 GOOGLE_API_KEY。請到 Streamlit Cloud 的 Secrets 設定。")

    text_prompt = (
        f'你是一個專業的英文老師。請針對單字 "{target_word}" 提供：詞性、中文解釋、一段結合「葬送的芙莉蓮」奇幻風格與魔法感的圖像記憶口訣、以及一個適合學生的例句。'
        "請以 JSON 格式回傳：pos, definition, mnemonic, example, exampleCn。請使用繁體中文。"
    )

    text_url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    )
    text_payload = {
        "contents": [{"parts": [{"text": text_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    text_data = fetch_with_retry(text_url, text_payload)

    raw_text = text_data["candidates"][0]["content"]["parts"][0]["text"]
    content = json.loads(raw_text)

    image_prompt = (
        f'Masterpiece illustration for word "{target_word}" in "Frieren: Beyond Journey\'s End" art style. '
        f"Scene: {content['mnemonic']}. Ethereal golden lighting, high fantasy magic, detailed line art. No text."
    )

    image_url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/imagen-4.0-generate-001:predict?key={api_key}"
    )
    image_payload = {
        "instances": [{"prompt": image_prompt}],
        "parameters": {"sampleCount": 1},
    }

    image_b64 = ""
    try:
        image_data = fetch_with_retry(image_url, image_payload)
        predictions = image_data.get("predictions", [])
        if predictions:
            image_b64 = predictions[0].get("bytesBase64Encoded", "")
    except Exception:
        image_b64 = ""

    final_result = {
        "word": target_word,
        **content,
        "image_b64": image_b64,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }
    st.session_state["result"] = final_result
    save_to_history(final_result)


def speak_button(text: str, label: str, key: str) -> None:
    safe = json.dumps(text)
    js = f"""
    <script>
    function speakText_{key}() {{
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance({safe});
        u.lang = 'en-US';
        u.rate = 0.85;
        window.speechSynthesis.speak(u);
    }}
    </script>
    <button onclick="speakText_{key}()" style="
        background: linear-gradient(135deg,#fbbf24,#d97706);
        border:none;border-radius:999px;padding:0.55rem 0.85rem;
        color:#020617;font-weight:800;cursor:pointer;">{label}</button>
    """
    st.components.v1.html(js, height=52)


def render_result() -> None:
    result = st.session_state["result"]
    if not result:
        return

    col1, col2 = st.columns([1.05, 1.0], gap="large")
    with col1:
        st.markdown('<div class="magic-card">', unsafe_allow_html=True)
        if result.get("image_b64"):
            image_bytes = base64.b64decode(result["image_b64"])
            st.image(image_bytes, use_container_width=True)
        else:
            st.info("本次沒有成功生成圖片，但文字內容已完成。")
        st.markdown(
            f'<div class="big-word">{result.get("word", "")}</div>',
            unsafe_allow_html=True,
        )
        speak_button(result.get("word", ""), "🔊 發音", "word")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="magic-card">', unsafe_allow_html=True)
        st.markdown(
            f'<span class="word-chip">{result.get("pos", "")}</span>'
            f'<div class="big-word" style="font-size:2.2rem">{result.get("definition", "")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-title">記憶咒語</div>', unsafe_allow_html=True)
        st.write(result.get("mnemonic", ""))
        st.markdown('<div class="section-title">魔法實踐</div>', unsafe_allow_html=True)
        st.write(f'“{result.get("example", "")}”')
        speak_button(result.get("example", ""), "🔊 例句朗讀", "example")
        st.caption(result.get("exampleCn", ""))
        st.markdown('</div>', unsafe_allow_html=True)


def render_history() -> None:
    st.markdown('<div class="title-box"><h2>學識長廊</h2></div>', unsafe_allow_html=True)
    history = st.session_state["history"]
    st.write(f"目前收藏：**{len(history)}**")
    if not history:
        st.info("目前還沒有收藏紀錄。")
        return

    for idx, item in enumerate(history):
        with st.container():
            st.markdown('<div class="history-box">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([3.2, 1.1, 1.1])
            with c1:
                st.markdown(f"**{item.get('word','')}** ｜ {item.get('definition','')}")
                st.caption(item.get("example", ""))
            with c2:
                if st.button("查看", key=f"view_{idx}", use_container_width=True):
                    st.session_state["result"] = item
                    st.session_state["active_tab"] = "探求"
                    st.rerun()
            with c3:
                if st.button("刪除", key=f"del_{idx}", use_container_width=True):
                    delete_from_history(item.get("word", ""))
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def render_explore() -> None:
    st.markdown(
        '<div class="title-box"><h1>✨ Frieren Spellbook</h1><div class="small-note">魔法風格英文單字學習工具</div></div>',
        unsafe_allow_html=True,
    )

    render_result()

    st.markdown('<div class="magic-card">', unsafe_allow_html=True)
    top1, top2 = st.columns([1.3, 2.2], gap="large")
    with top1:
        st.subheader("教育部 2000 必修單字")
        st.caption("點擊分類與單字，快速召喚學習內容")
    with top2:
        cat_cols = st.columns(len(MOE_VOCAB_BASE) + 1)
        for i, cat in enumerate(MOE_VOCAB_BASE.keys()):
            if cat_cols[i].button(cat, key=f"cat_{cat}", use_container_width=True):
                generate_random_five(cat)
                st.rerun()
        if cat_cols[-1].button("隨機", key="random_cat", use_container_width=True):
            pick_random_category()
            st.rerun()

    st.write(f"目前分類：**{st.session_state['current_category']}**")
    word_cols = st.columns(5)
    for i, w in enumerate(st.session_state["suggested_words"]):
        if word_cols[i].button(w, key=f"word_{w}", use_container_width=True):
            with st.spinner("正在擷取魔法意象..."):
                fetch_ai_content(w)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="magic-card">', unsafe_allow_html=True)
    st.subheader("手動輸入單字")
    col_input, col_btn = st.columns([4.2, 1.1])
    with col_input:
        word = st.text_input("輸入單字", value=st.session_state.get("word_input", ""), label_visibility="collapsed", placeholder="輸入意欲學習之單字...")
        st.session_state["word_input"] = word
    with col_btn:
        trigger = st.button("召喚", use_container_width=True)

    if trigger and word.strip():
        with st.spinner("正在擷取魔法意象..."):
            fetch_ai_content(word.strip())
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    inject_css()
    init_session()

    active = st.radio("切換頁籤", ["探求", "圖鑑"], index=0 if st.session_state["active_tab"] == "探求" else 1, horizontal=True, label_visibility="collapsed")
    st.session_state["active_tab"] = active

    try:
        if active == "探求":
            render_explore()
        else:
            render_history()
    except Exception as exc:  # noqa: BLE001
        st.markdown(
            f'<div class="error-box">⚠️ 魔法召喚中斷：{str(exc)}</div>',
            unsafe_allow_html=True,
        )
        st.exception(exc)

    with st.sidebar:
        st.markdown("### 使用說明")
        st.write("1. 點選分類推薦單字或自行輸入單字。")
        st.write("2. 程式會呼叫 Gemini 產生單字解析與記憶口訣。")
        st.write("3. 再呼叫 Imagen 產生記憶圖片。")
        st.write("4. 歷史紀錄會保存在本次 Session 中。")
        st.markdown("### Secrets")
        st.code('GOOGLE_API_KEY = "your_api_key"')


if __name__ == "__main__":
    main()
