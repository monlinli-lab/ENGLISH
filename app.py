import os
import json
import random
import base64
from datetime import datetime
from typing import Dict, List, Any

import requests
import streamlit as st
import streamlit.components.v1 as components

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Frieren Spellbook",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Constants
# -----------------------------
MOE_VOCAB_BASE: Dict[str, List[str]] = {
    "動物與昆蟲": ["butterfly", "elephant", "dolphin", "mosquito", "squirrel", "dinosaur", "giraffe", "kangaroo", "penguin", "rabbit"],
    "食物與餐飲": ["hamburger", "sandwich", "spaghetti", "breakfast", "vegetable", "chocolate", "delicious", "restaurant", "strawberry", "cabbage"],
    "情緒與性格": ["confident", "generous", "impatient", "nervous", "cheerful", "frightened", "embarrassed", "energetic", "friendly", "selfish"],
    "動作與行為": ["celebrate", "describe", "experience", "imagine", "practice", "remember", "understand", "whisper", "complain", "encourage"],
    "環境與自然": ["mountain", "waterfall", "environment", "temperature", "volcano", "weather", "sunshine", "rainbow", "ocean", "forest"],
    "生活與居家": ["furniture", "refrigerator", "microwave", "blanket", "apartment", "balcony", "neighborhood", "curtain", "flashlight", "toothbrush"],
}

DEFAULT_RESULT = {
    "pos": "unknown",
    "definition": "暫無定義",
    "mnemonic": "暫時無法從魔法書中召喚記憶口訣。",
    "example": "This is a sample sentence.",
    "exampleCn": "這是一個範例句子。",
    "image_base64": "",
}

# -----------------------------
# Helpers
# -----------------------------
def get_api_key() -> str:
    return st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))


def init_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "result" not in st.session_state:
        st.session_state.result = None
    if "current_category" not in st.session_state:
        st.session_state.current_category = random.choice(list(MOE_VOCAB_BASE.keys()))
    if "suggested_words" not in st.session_state:
        st.session_state.suggested_words = []
        generate_random_five(st.session_state.current_category)
    if "tab" not in st.session_state:
        st.session_state.tab = "探求"


def generate_random_five(category: str) -> None:
    pool = MOE_VOCAB_BASE[category][:]
    random.shuffle(pool)
    st.session_state.current_category = category
    st.session_state.suggested_words = pool[:5]


def pick_random_category() -> None:
    category = random.choice(list(MOE_VOCAB_BASE.keys()))
    generate_random_five(category)


def save_to_history(item: Dict[str, Any]) -> None:
    current = st.session_state.history
    new_history = [item] + [h for h in current if h.get("word") != item.get("word")]
    st.session_state.history = new_history[:20]


def delete_from_history(word_to_delete: str) -> None:
    st.session_state.history = [h for h in st.session_state.history if h.get("word") != word_to_delete]


def call_gemini_json(target_word: str, api_key: str) -> Dict[str, Any]:
    text_prompt = f'''你是一個專業的英文老師。請針對單字 "{target_word}" 提供：
1. 詞性
2. 中文解釋
3. 一段結合「葬送的芙莉蓮」奇幻風格與魔法感的圖像記憶口訣
4. 一個適合學生的英文例句
5. 該例句的繁體中文翻譯

請務必只輸出 JSON，格式如下：
{{
  "pos": "...",
  "definition": "...",
  "mnemonic": "...",
  "example": "...",
  "exampleCn": "..."
}}
請使用繁體中文。'''

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": text_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.8,
        },
    }
    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw_text)


def call_imagen_base64(target_word: str, mnemonic: str, api_key: str) -> str:
    image_prompt = (
        f'Masterpiece illustration for the vocabulary word "{target_word}" '
        f'in a high fantasy anime style inspired by melancholic magic adventure. '
        f'Scene: {mnemonic}. Ethereal golden lighting, detailed line art, dreamy atmosphere, no text.'
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
    payload = {
        "instances": [{"prompt": image_prompt}],
        "parameters": {"sampleCount": 1},
    }

    response = requests.post(url, json=payload, timeout=90)
    if not response.ok:
        return ""

    data = response.json()
    try:
        return data["predictions"][0]["bytesBase64Encoded"]
    except Exception:
        return ""


def fetch_ai_content(target_word: str) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未偵測到 GOOGLE_API_KEY。請在 Streamlit secrets 或環境變數中設定。")

    content = call_gemini_json(target_word, api_key)
    image_base64 = call_imagen_base64(target_word, content.get("mnemonic", ""), api_key)

    final_result = {
        "word": target_word,
        "pos": content.get("pos", DEFAULT_RESULT["pos"]),
        "definition": content.get("definition", DEFAULT_RESULT["definition"]),
        "mnemonic": content.get("mnemonic", DEFAULT_RESULT["mnemonic"]),
        "example": content.get("example", DEFAULT_RESULT["example"]),
        "exampleCn": content.get("exampleCn", DEFAULT_RESULT["exampleCn"]),
        "image_base64": image_base64,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return final_result


def speak_button(text: str, label: str, key: str) -> None:
    safe_text = json.dumps(text)
    components.html(
        f"""
        <button onclick='window.speechSynthesis.cancel();
                          const u = new SpeechSynthesisUtterance({safe_text});
                          u.lang = "en-US";
                          u.rate = 0.85;
                          window.speechSynthesis.speak(u);'
                style='background:#f59e0b;color:#111827;border:none;border-radius:999px;padding:10px 14px;cursor:pointer;font-weight:700;'>
            {label}
        </button>
        """,
        height=48,
        key=key,
    )


def result_card(result: Dict[str, Any]) -> None:
    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.markdown(f"### ✨ {result['word']}")
        if result.get("image_base64"):
            image_bytes = base64.b64decode(result["image_base64"])
            st.image(image_bytes, use_container_width=True)
        else:
            st.info("本次未成功生成圖片，但文字內容已成功召喚。")

        speak_button(result["word"], "🔊 單字發音", key=f"speak_word_{result['word']}")

    with right:
        st.markdown(
            f"""
            <div style="padding:20px;border:1px solid rgba(245,158,11,.25);border-radius:22px;background:rgba(15,23,42,.55)">
                <div style="display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(245,158,11,.12);color:#fbbf24;font-size:12px;font-weight:700">{result['pos']}</div>
                <h2 style="margin:12px 0 6px 0">{result['definition']}</h2>
                <p style="color:#cbd5e1;margin:0">查詢時間：{result['timestamp']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("#### 💡 記憶咒語")
        st.write(result["mnemonic"])
        st.markdown("#### 📘 魔法實踐")
        st.write(f'“{result["example"]}”')
        speak_button(result["example"], "🔊 例句發音", key=f"speak_example_{result['word']}")
        st.caption(result["exampleCn"])


def history_view() -> None:
    st.subheader("📚 學識長廊")
    st.caption(f"已收藏 {len(st.session_state.history)} 筆單字")

    if not st.session_state.history:
        st.info("目前還沒有收藏紀錄。")
        return

    cols = st.columns(3)
    for idx, item in enumerate(st.session_state.history):
        with cols[idx % 3]:
            with st.container(border=True):
                if item.get("image_base64"):
                    try:
                        st.image(base64.b64decode(item["image_base64"]), use_container_width=True)
                    except Exception:
                        pass
                st.markdown(f"**{item['word']}**")
                st.write(item["definition"])
                st.caption(item["pos"])
                st.caption(item["example"])
                c1, c2 = st.columns(2)
                if c1.button("查看", key=f"view_{item['word']}"):
                    st.session_state.result = item
                    st.session_state.tab = "探求"
                    st.rerun()
                if c2.button("刪除", key=f"delete_{item['word']}"):
                    delete_from_history(item["word"])
                    st.rerun()


# -----------------------------
# UI
# -----------------------------
init_state()

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top, rgba(120,53,15,.18), rgba(2,6,23,1) 42%), #020617;
    }
    .block-container {padding-top: 1.8rem; padding-bottom: 6rem; max-width: 1200px;}
    h1, h2, h3 {letter-spacing: .02em;}
    [data-testid="stButton"] button {
        border-radius: 16px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("✨ Frieren Spellbook")
st.caption("將 React 版本改寫為 Streamlit，可直接部署到 GitHub + Streamlit Cloud。")

if not get_api_key():
    st.warning("尚未設定 GOOGLE_API_KEY。畫面可正常開啟，但查詢 AI 內容時會失敗。")

selected_tab = st.segmented_control(
    "功能選單",
    options=["探求", "圖鑑"],
    default=st.session_state.tab,
    key="tab_selector",
)
st.session_state.tab = selected_tab

if st.session_state.tab == "探求":
    if st.session_state.result:
        result_card(st.session_state.result)
        st.divider()

    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("教育部 2000 必修單字")
        st.caption("點一下即可召喚單字內容")
    with right:
        if st.button("🔄 隨機切換分類", use_container_width=True):
            pick_random_category()
            st.rerun()

    category_cols = st.columns(len(MOE_VOCAB_BASE))
    for idx, cat in enumerate(MOE_VOCAB_BASE.keys()):
        with category_cols[idx]:
            if st.button(cat, use_container_width=True, key=f"cat_{cat}"):
                generate_random_five(cat)
                st.rerun()

    st.caption(f"目前分類：{st.session_state.current_category}")

    word_cols = st.columns(5)
    for idx, w in enumerate(st.session_state.suggested_words):
        with word_cols[idx]:
            if st.button(w, use_container_width=True, key=f"word_{w}"):
                with st.spinner("正在擷取魔法意象與單字解釋..."):
                    try:
                        result = fetch_ai_content(w)
                        st.session_state.result = result
                        save_to_history(result)
                        st.rerun()
                    except Exception as e:
                        st.error(f"魔力不穩定：{e}")

    st.divider()
    st.subheader("手動輸入單字")
    user_word = st.text_input("輸入想學習的英文單字", placeholder="例如：butterfly")
    if st.button("✨ 召喚", type="primary", use_container_width=True, disabled=not user_word.strip()):
        with st.spinner("正在從阿卡西紀錄中檢索單字..."):
            try:
                result = fetch_ai_content(user_word.strip())
                st.session_state.result = result
                save_to_history(result)
                st.rerun()
            except Exception as e:
                st.error(f"魔力不穩定：{e}")
else:
    history_view()
