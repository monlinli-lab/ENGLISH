# Frieren Spellbook（Streamlit 版）

這是把你提供的 React 英文單字學習工具，改寫成可直接部署的 **Streamlit 專案**。

## 專案內容

- `app.py`：主程式
- `requirements.txt`：套件需求
- `.streamlit/config.toml`：Streamlit 主題設定
- `README.md`：部署說明

## 本地執行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 部署

1. 將整個專案上傳到 GitHub
2. 到 Streamlit Community Cloud 建立新 app
3. 主檔案填入：`app.py`
4. 在 **Secrets** 中加入：

```toml
GOOGLE_API_KEY = "你的 Google AI API Key"
```

## 說明

此版本保留原本的核心功能：

- 教育部 2000 單字分類抽取
- AI 生成詞性、中文解釋、記憶口訣、例句
- AI 圖片生成
- 查詢歷史紀錄
- 英文單字與例句發音

## 注意事項

1. 若未設定 `GOOGLE_API_KEY`，畫面仍可開啟，但查詢功能會失敗。
2. Streamlit 並沒有瀏覽器版 React 的 `localStorage`，因此這版歷史紀錄以 **當前 session** 為主；重新整理或重開部署環境後，可能會消失。
3. 若 Imagen 模型端點日後變更，可只調整 `app.py` 內的 API URL。

