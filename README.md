# Frieren Spellbook - Streamlit 版

這是將你提供的 React 單字學習工具，改寫成可直接上傳 GitHub 並部署到 Streamlit Cloud 的版本。

## 專案結構

- `app.py`：主程式
- `requirements.txt`：Python 套件需求
- `.streamlit/config.toml`：Streamlit 介面設定
- `README.md`：部署說明

## 功能

- 教育部 2000 必修單字分類推薦
- 自行輸入英文單字查詢
- Gemini 產生：詞性、中文解釋、記憶口訣、例句、例句翻譯
- Imagen 產生圖像記憶圖片
- 發音按鈕（單字與例句）
- 圖鑑歷史紀錄（同一個 session 內保留）
- API 請求失敗時自動重試

## GitHub 上傳方式

1. 解壓縮此專案包
2. 上傳整個資料夾到 GitHub repository
3. 確認根目錄有 `app.py`

## Streamlit Cloud 部署方式

1. 到 Streamlit Cloud 建立新 App
2. Repository 指向這個 GitHub 專案
3. Main file path 填入：`app.py`
4. 到 App 的 **Secrets** 加入：

```toml
GOOGLE_API_KEY = "你的 Google API Key"
```

## 注意事項

### 1. API Key 必須自行設定
此版本和你原本的 React 邏輯一致，程式本身不硬寫金鑰，部署時請在 Secrets 中設定。

### 2. 歷史紀錄差異
原本 React 版本使用 `localStorage`。Streamlit 版改為 `st.session_state`，因此：

- 重新整理或重開 session 後，歷史紀錄會重置
- 若要永久保存，之後可再幫你改成寫入 JSON / SQLite

### 3. Imagen API
Google Imagen 的 API 格式有時會依版本調整。如果未來 Google 端變更回應格式，可能需要微調 `app.py`。

## 本地執行

```bash
pip install -r requirements.txt
streamlit run app.py
```

如果你要，我下一步也可以再幫你做成：

- **真正可永久保存歷史紀錄的版本**
- **免 API Key 的版本（改用搜尋與本地資料生成文字內容）**
- **更接近你原始 React 視覺效果的豪華 UI 版**
