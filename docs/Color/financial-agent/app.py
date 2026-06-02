from __future__ import annotations

import os
import random
import time
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


PALETTE = {
    "bg": "#0F0F0F",
    "purple": "#6B46C1",
    "blue": "#2563EB",
    "pink": "#FF0080",
    "lime": "#84CC16",
    "text": "#E5E7EB",
    "muted": "#A1A1AA",
}


def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Sora:wght@400;600;700&display=swap');

        :root {{
            --bg: {PALETTE['bg']};
            --purple: {PALETTE['purple']};
            --blue: {PALETTE['blue']};
            --pink: {PALETTE['pink']};
            --lime: {PALETTE['lime']};
            --text: {PALETTE['text']};
            --muted: {PALETTE['muted']};
            --glass: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.18);
        }}

        html, body, [class*="css"]  {{
            font-family: 'Space Grotesk', 'Sora', 'Avenir Next', sans-serif;
            color: var(--text);
        }}

        [data-testid="stAppViewContainer"] > .main {{
            background:
                radial-gradient(circle at 20% 10%, rgba(107, 70, 193, 0.32), transparent 35%),
                radial-gradient(circle at 80% 0%, rgba(37, 99, 235, 0.35), transparent 35%),
                radial-gradient(circle at 90% 90%, rgba(255, 0, 128, 0.18), transparent 30%),
                var(--bg);
            animation: fadeIn 0.7s ease-out;
        }}

        [data-testid="stHeader"], [data-testid="stToolbar"] {{
            background: transparent;
        }}

        section[data-testid="stSidebar"] > div {{
            background: linear-gradient(180deg, rgba(107, 70, 193, 0.24), rgba(15, 15, 15, 0.96));
            border-right: 1px solid rgba(255,255,255,0.12);
        }}

        .hero {{
            border: 1px solid var(--glass-border);
            background: linear-gradient(120deg, rgba(107, 70, 193, 0.34), rgba(37, 99, 235, 0.18));
            backdrop-filter: blur(14px);
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
            animation: riseIn 0.5s ease-out;
        }}

        .hero h1 {{
            margin: 0;
            color: white;
            font-weight: 700;
            letter-spacing: 0.2px;
        }}

        .hero p {{
            margin: 6px 0 0;
            color: var(--muted);
            font-size: 0.95rem;
        }}

        div[data-testid="stMetric"] {{
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 14px;
            padding: 6px 8px;
            backdrop-filter: blur(10px);
            animation: riseIn 0.45s ease-out;
        }}

        div[data-testid="stMetricLabel"] p {{
            color: var(--muted);
        }}

        div[data-testid="stMetricValue"] {{
            color: white;
        }}

        .panel-title {{
            font-size: 1.05rem;
            color: white;
            margin-bottom: 6px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }}

        .chip {{
            display: inline-block;
            padding: 4px 10px;
            margin-right: 8px;
            border-radius: 999px;
            background: rgba(255, 0, 128, 0.16);
            border: 1px solid rgba(255, 0, 128, 0.5);
            color: #ffd9ee;
            font-size: 0.78rem;
        }}

        .chip.lime {{
            background: rgba(132, 204, 22, 0.18);
            border-color: rgba(132, 204, 22, 0.5);
            color: #e8ffbf;
        }}

        [data-baseweb="tab-list"] {{
            gap: 8px;
        }}

        [data-baseweb="tab"] {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 8px 14px;
        }}

        [data-baseweb="tab-highlight"] {{
            background-color: var(--pink);
        }}

        @keyframes riseIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_symbols(value: str) -> list[str]:
    symbols = [v.strip().upper() for v in value.split(",") if v.strip()]
    return symbols[:12] if symbols else ["AAPL", "MSFT", "NVDA", "TSLA", "BTC-USD"]


def parse_topics(value: str) -> list[str]:
    topics = [v.strip() for v in value.split(",") if v.strip()]
    return topics[:10] if topics else ["美联储", "AI", "半导体", "新能源", "加密资产"]


def init_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "我是你的金融AI助手。你可以问我行情、仓位风险、板块动量和舆论变化。",
            }
        ]

    if "market_store" not in st.session_state:
        st.session_state.market_store = {}

    if "sentiment_store" not in st.session_state:
        st.session_state.sentiment_store = {}

    if "warned_market_endpoint" not in st.session_state:
        st.session_state.warned_market_endpoint = False

    if "warned_sentiment_endpoint" not in st.session_state:
        st.session_state.warned_sentiment_endpoint = False


def _initial_price(symbol: str) -> float:
    if "BTC" in symbol:
        return random.uniform(38000, 72000)
    if "ETH" in symbol:
        return random.uniform(1800, 4200)
    return random.uniform(20, 800)


def simulate_market(symbols: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    store = st.session_state.market_store

    for symbol in symbols:
        if symbol not in store:
            base = _initial_price(symbol)
            store[symbol] = {
                "open": base,
                "price": base,
                "volume": random.randint(120_000, 5_000_000),
                "history": [],
            }

        row = store[symbol]
        shock = random.gauss(0, 0.0038)
        row["price"] = max(0.1, row["price"] * (1 + shock))
        row["volume"] = max(10_000, int(row["volume"] * (1 + random.gauss(0, 0.09))))

        ts = datetime.now().strftime("%H:%M:%S")
        row["history"].append({"time": ts, "price": round(row["price"], 4)})
        row["history"] = row["history"][-120:]

        out.append(
            {
                "symbol": symbol,
                "price": round(row["price"], 4),
                "change_pct": ((row["price"] / row["open"]) - 1) * 100,
                "volume": int(row["volume"]),
                "time": ts,
            }
        )

    return out


def simulate_sentiment(topics: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    store = st.session_state.sentiment_store

    for topic in topics:
        if topic not in store:
            score = random.uniform(-0.15, 0.25)
            mentions = random.randint(60, 800)
            store[topic] = {"score": score, "mentions": mentions, "history": []}

        row = store[topic]
        row["score"] = max(-1.0, min(1.0, row["score"] + random.gauss(0, 0.08)))
        row["mentions"] = max(5, int(row["mentions"] + random.gauss(0, 45)))

        ts = datetime.now().strftime("%H:%M:%S")
        row["history"].append({"time": ts, "score": row["score"]})
        row["history"] = row["history"][-120:]

        if row["score"] > 0.35:
            label = "明显偏多"
        elif row["score"] > 0.05:
            label = "轻度偏多"
        elif row["score"] < -0.35:
            label = "明显偏空"
        elif row["score"] < -0.05:
            label = "轻度偏空"
        else:
            label = "中性"

        out.append(
            {
                "topic": topic,
                "score": round(row["score"], 3),
                "mentions": int(row["mentions"]),
                "label": label,
                "time": ts,
            }
        )

    return out


def fetch_market(symbols: list[str], endpoint: str) -> list[dict[str, Any]]:
    if endpoint:
        try:
            resp = requests.get(
                endpoint,
                params={"symbols": ",".join(symbols)},
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data
        except Exception:
            if not st.session_state.warned_market_endpoint:
                st.sidebar.warning("行情API不可用，已切换到本地模拟数据。")
                st.session_state.warned_market_endpoint = True

    return simulate_market(symbols)


def fetch_sentiment(topics: list[str], endpoint: str) -> list[dict[str, Any]]:
    if endpoint:
        try:
            resp = requests.get(
                endpoint,
                params={"topics": ",".join(topics)},
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data
        except Exception:
            if not st.session_state.warned_sentiment_endpoint:
                st.sidebar.warning("舆论API不可用，已切换到本地模拟数据。")
                st.session_state.warned_sentiment_endpoint = True

    return simulate_sentiment(topics)


def local_reply(prompt: str, market_df: pd.DataFrame, sentiment_df: pd.DataFrame) -> str:
    prompt_l = prompt.lower()
    mover = market_df.iloc[market_df["change_pct"].abs().idxmax()]
    top_sent = sentiment_df.iloc[sentiment_df["score"].abs().idxmax()]

    mentioned_symbol = None
    for sym in market_df["symbol"].tolist():
        if sym.lower() in prompt_l:
            mentioned_symbol = sym
            break

    lines = [
        "以下是基于当前看板的即时解读：",
        f"- 最大波动标的是 `{mover['symbol']}`，涨跌幅 `{mover['change_pct']:+.2f}%`。",
        f"- 舆论强度最高主题是 `{top_sent['topic']}`，情绪值 `{top_sent['score']:+.2f}`（{top_sent['label']}）。",
    ]

    if mentioned_symbol is not None:
        row = market_df[market_df["symbol"] == mentioned_symbol].iloc[0]
        lines.append(
            f"- 你关注的 `{mentioned_symbol}` 现价 `{row['price']:.2f}`，日内 `{row['change_pct']:+.2f}%`，成交量 `{int(row['volume']):,}`。"
        )

    if any(k in prompt for k in ["风险", "回撤", "止损"]):
        lines.append("- 风控建议：先定义最大单日回撤阈值，再根据波动分层减仓。")

    if any(k in prompt for k in ["机会", "策略", "买", "卖"]):
        lines.append("- 交易建议：先用看板确认“价量同向 + 情绪同向”，再决定是否分批执行。")

    lines.append("- 如需更精确结论，可在侧边栏接入真实行情/舆情 API。")
    return "\n".join(lines)


def call_chat_api(chat_api_url: str, prompt: str, market: list[dict[str, Any]], sentiment: list[dict[str, Any]]) -> str | None:
    if not chat_api_url:
        return None

    payload = {
        "message": prompt,
        "messages": st.session_state.chat_messages[-12:],
        "context": {
            "market": market,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
        },
    }
    try:
        resp = requests.post(chat_api_url, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("reply"), str):
            return data["reply"]
    except Exception:
        st.sidebar.warning("对话API暂不可用，当前使用本地分析回复。")

    return None


def render_market_tab(market_df: pd.DataFrame) -> None:
    st.markdown('<div class="panel-title">Market Pulse</div>', unsafe_allow_html=True)
    cols = st.columns(min(4, len(market_df)))
    for idx, row in market_df.head(4).iterrows():
        cols[idx].metric(
            label=row["symbol"],
            value=f"{row['price']:.2f}",
            delta=f"{row['change_pct']:+.2f}%",
        )

    hist_rows = []
    for symbol, row in st.session_state.market_store.items():
        for point in row["history"][-50:]:
            hist_rows.append({"symbol": symbol, "time": point["time"], "price": point["price"]})
    hist_df = pd.DataFrame(hist_rows)

    if not hist_df.empty:
        fig = px.line(
            hist_df,
            x="time",
            y="price",
            color="symbol",
            color_discrete_sequence=[PALETTE["blue"], PALETTE["purple"], PALETTE["pink"], "#4ADE80", "#38BDF8"],
        )
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=12, r=12, t=28, b=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            legend_title_text="",
            title="价格轨迹（最近50个采样点）",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        market_df.sort_values("change_pct", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "price": st.column_config.NumberColumn("Price", format="%.4f"),
            "change_pct": st.column_config.NumberColumn("Change %", format="%.2f%%"),
            "volume": st.column_config.NumberColumn("Volume", format="%d"),
        },
    )


def render_sentiment_tab(sentiment_df: pd.DataFrame) -> None:
    st.markdown('<div class="panel-title">Sentiment Radar</div>', unsafe_allow_html=True)

    bar = go.Figure(
        go.Bar(
            x=sentiment_df["score"],
            y=sentiment_df["topic"],
            orientation="h",
            marker=dict(
                color=sentiment_df["score"],
                colorscale=[
                    [0.0, "#FF0080"],
                    [0.5, "#6B46C1"],
                    [1.0, "#84CC16"],
                ],
                cmin=-1,
                cmax=1,
            ),
        )
    )
    bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        margin=dict(l=12, r=12, t=20, b=12),
        title="主题情绪值（-1 到 +1）",
        xaxis_title="Sentiment Score",
        yaxis_title="",
    )
    st.plotly_chart(bar, use_container_width=True)

    bubble = px.scatter(
        sentiment_df,
        x="score",
        y="mentions",
        color="topic",
        size="mentions",
        hover_data=["label"],
        color_discrete_sequence=[PALETTE["blue"], PALETTE["purple"], PALETTE["pink"], "#4ADE80", "#22D3EE"],
    )
    bubble.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        margin=dict(l=12, r=12, t=20, b=12),
        title="讨论热度 vs 情绪值",
        xaxis_title="Sentiment Score",
        yaxis_title="Mentions",
    )
    st.plotly_chart(bubble, use_container_width=True)

    trend_rows = []
    for topic, row in st.session_state.sentiment_store.items():
        for point in row["history"][-50:]:
            trend_rows.append({"topic": topic, "time": point["time"], "score": point["score"]})

    trend_df = pd.DataFrame(trend_rows)
    if not trend_df.empty:
        trend = px.line(
            trend_df,
            x="time",
            y="score",
            color="topic",
            color_discrete_sequence=[PALETTE["lime"], PALETTE["pink"], PALETTE["blue"], PALETTE["purple"], "#F59E0B"],
        )
        trend.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            margin=dict(l=12, r=12, t=20, b=12),
            title="情绪变化轨迹",
            xaxis_title="Time",
            yaxis_title="Score",
        )
        st.plotly_chart(trend, use_container_width=True)

    st.dataframe(
        sentiment_df.sort_values("score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def stream_reply(text: str) -> str:
    holder = st.empty()
    built = ""
    for token in text.split(" "):
        built += token + " "
        holder.markdown(built + "▌")
        time.sleep(0.015)
    holder.markdown(built)
    return built.strip()


def main() -> None:
    st.set_page_config(page_title="Financial AI Assistant", page_icon="📈", layout="wide")
    inject_theme()
    init_state()

    with st.sidebar:
        st.markdown("### Control Tower")
        watchlist = parse_symbols(
            st.text_input("Watchlist", value="AAPL,MSFT,NVDA,TSLA,BTC-USD,ETH-USD")
        )
        topics = parse_topics(
            st.text_input("Sentiment Topics", value="美联储,AI,半导体,新能源,加密资产")
        )
        auto_refresh = st.toggle("Auto Refresh", value=True)
        refresh_s = st.slider("Refresh Interval (sec)", min_value=2, max_value=20, value=4)

        st.markdown("### API Endpoints (Optional)")
        market_api = st.text_input("Market API URL", value=os.getenv("MARKET_API_URL", ""))
        sentiment_api = st.text_input("Sentiment API URL", value=os.getenv("SENTIMENT_API_URL", ""))
        chat_api = st.text_input("Chat API URL", value=os.getenv("CHAT_API_URL", ""))

        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chat_messages = [
                {
                    "role": "assistant",
                    "content": "会话已重置。告诉我你现在最关注的资产或策略。",
                }
            ]
            st.rerun()

    market = fetch_market(watchlist, market_api)
    sentiment = fetch_sentiment(topics, sentiment_api)
    market_df = pd.DataFrame(market)
    sentiment_df = pd.DataFrame(sentiment)

    st.markdown(
        """
        <div class="hero">
            <h1>Neon Finance Copilot</h1>
            <p>多轮对话 + 实时行情 + 舆论雷达。可直接接入你自己的后端数据与LLM服务。</p>
        </div>
        <div>
            <span class="chip">Live Market</span>
            <span class="chip lime">Sentiment Radar</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_chat, tab_market, tab_sentiment = st.tabs([
        "AI 对话",
        "实时行情看板",
        "舆论看板",
    ])

    with tab_chat:
        left, right = st.columns([1.65, 1.0], gap="large")

        with left:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            prompt = st.chat_input("例如：分析一下 NVDA 和半导体板块当前风险")
            if prompt:
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("分析中..."):
                        remote = call_chat_api(chat_api, prompt, market, sentiment)
                        reply = remote if remote else local_reply(prompt, market_df, sentiment_df)
                        streamed = stream_reply(reply)

                st.session_state.chat_messages.append({"role": "assistant", "content": streamed})

        with right:
            st.markdown('<div class="panel-title">Quick Signal</div>', unsafe_allow_html=True)
            top_up = market_df.sort_values("change_pct", ascending=False).iloc[0]
            top_dn = market_df.sort_values("change_pct", ascending=True).iloc[0]
            hot_topic = sentiment_df.sort_values("mentions", ascending=False).iloc[0]
            sentiment_peak = sentiment_df.iloc[sentiment_df["score"].abs().idxmax()]

            st.metric("Top Gainer", f"{top_up['symbol']} {top_up['price']:.2f}", f"{top_up['change_pct']:+.2f}%")
            st.metric("Top Loser", f"{top_dn['symbol']} {top_dn['price']:.2f}", f"{top_dn['change_pct']:+.2f}%")
            st.metric("Most Discussed", f"{hot_topic['topic']}", f"mentions {int(hot_topic['mentions'])}")
            st.metric("Strongest Sentiment", sentiment_peak["topic"], f"{sentiment_peak['score']:+.2f}")
            st.caption(f"更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with tab_market:
        render_market_tab(market_df)

    with tab_sentiment:
        render_sentiment_tab(sentiment_df)

    if auto_refresh:
        st.caption(f"Auto refresh enabled: next update in {refresh_s} seconds")
        time.sleep(refresh_s)
        st.rerun()


if __name__ == "__main__":
    main()
