# Financial Agent Frontend (Streamlit)

一个金融 AI 助手前端，包含：

- 多轮对话（支持本地回复或接入后端对话 API）
- 实时行情看板（可接行情 API，默认本地模拟）
- 舆论看板（可接舆情 API，默认本地模拟）

视觉风格使用：

- 深紫 `#6B46C1` 到电蓝 `#2563EB` 渐变
- 深色背景 `#0F0F0F`
- 霓虹粉 `#FF0080` 强调
- 青柠绿 `#84CC16` 高亮
- 玻璃拟态 + 未来感

## Run

```bash
cd financial-agent
pip install -r requirements.txt
streamlit run app.py
```

## Optional backend APIs

你可以在侧边栏输入下面三个 URL，也可以通过环境变量传入：

- `MARKET_API_URL`
- `SENTIMENT_API_URL`
- `CHAT_API_URL`

### Market API 返回格式（list）

```json
[
  {
    "symbol": "AAPL",
    "price": 238.14,
    "change_pct": 1.42,
    "volume": 22500123,
    "time": "15:01:09"
  }
]
```

### Sentiment API 返回格式（list）

```json
[
  {
    "topic": "AI",
    "score": 0.42,
    "mentions": 1280,
    "label": "明显偏多",
    "time": "15:01:09"
  }
]
```

### Chat API 返回格式（dict）

请求体会带 `message`、`messages`、`context`。返回：

```json
{
  "reply": "..."
}
```

## Notes

- 不接后端时，应用会自动使用本地模拟数据，方便先做前端联调。
- `Auto Refresh` 会按设定周期自动刷新看板。
