import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

LOG_FILE = "diet_log.csv"
MY_FOODS_FILE = "my_foods.csv"
SETTINGS_FILE = "diet_settings.json"
TZ = ZoneInfo("Asia/Tokyo")

DEFAULT_SETTINGS = {"kcal": 2100, "protein": 130}
LOG_COLUMNS = ["日付", "時刻", "区分", "食品名", "カロリー(kcal)", "タンパク質(g)"]
FOOD_COLUMNS = ["食品名", "カロリー(kcal)", "タンパク質(g)"]
MEALS = ["朝食", "昼食", "夕食", "間食"]
AMOUNTS = {"×0.5": 0.5, "×1": 1.0, "×1.5": 1.5, "×2": 2.0}

# よく食べる食品（日本食品標準成分表をもとにした目安値）
PRESET_FOODS = [
    ("ご飯 150g", 234, 3.8),
    ("食パン 6枚切1枚", 149, 5.3),
    ("卵 1個", 71, 6.1),
    ("納豆 1パック", 86, 7.4),
    ("豆腐 半丁", 110, 10.5),
    ("鶏むね肉 100g", 105, 23.3),
    ("ささみ 100g", 98, 23.9),
    ("サラダチキン 1個", 120, 25.0),
    ("鮭 1切れ", 99, 17.8),
    ("サバ缶 1缶", 261, 31.4),
    ("牛乳 200ml", 126, 6.8),
    ("ギリシャヨーグルト", 92, 10.0),
    ("プロテイン 1杯", 120, 22.0),
    ("バナナ 1本", 93, 1.1),
    ("味噌汁 1杯", 40, 2.5),
]


# ---------- データ読み書き ----------
def now():
    return datetime.now(TZ)


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False)


def load_csv(path, columns):
    if os.path.exists(path):
        return pd.read_csv(path, encoding="utf-8-sig")
    return pd.DataFrame(columns=columns)


def save_csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_log():
    df = load_csv(LOG_FILE, LOG_COLUMNS)
    df["日付"] = df["日付"].astype(str)
    return df


def add_entry(date, meal, name, kcal, protein):
    df = load_log()
    entry = {
        "日付": date.isoformat(),
        "時刻": now().strftime("%H:%M"),
        "区分": meal,
        "食品名": name,
        "カロリー(kcal)": round(float(kcal)),
        "タンパク質(g)": round(float(protein), 1),
    }
    save_csv(pd.concat([df, pd.DataFrame([entry])], ignore_index=True), LOG_FILE)
    st.session_state["toast"] = f"✅ {name} を追加（{entry['カロリー(kcal)']}kcal / P {entry['タンパク質(g)']}g）"


def all_foods():
    my = load_csv(MY_FOODS_FILE, FOOD_COLUMNS)
    foods = {r["食品名"]: (r["カロリー(kcal)"], r["タンパク質(g)"]) for _, r in my.iterrows()}
    for name, kcal, protein in PRESET_FOODS:
        foods.setdefault(name, (kcal, protein))
    return foods


def default_meal():
    h = now().hour
    if 4 <= h < 10:
        return "朝食"
    if 10 <= h < 15:
        return "昼食"
    if 17 <= h < 23:
        return "夕食"
    return "間食"


def summary_card(label, value, unit, ratio, color, note, goal):
    over = ratio > 1 and unit == "kcal"
    return (f'<div class="card"><div class="label">{label}</div>'
            f'<div class="value">{value}<span class="unit"> {unit} {goal}</span></div>'
            f'<div class="bar"><div style="width:{min(ratio, 1) * 100:.0f}%;'
            f'background:{"#e4572e" if over else color}"></div></div>'
            f'<div class="note">{note}</div></div>')


# ---------- コールバック ----------
def on_quick_add():
    name = st.session_state["quick_food"]
    if not name:
        return
    kcal, protein = all_foods()[name]
    rate = AMOUNTS[st.session_state["amount"] or "×1"]
    add_entry(st.session_state["log_date"], st.session_state["meal"] or default_meal(),
              name if rate == 1 else f"{name} {st.session_state['amount']}",
              kcal * rate, protein * rate)
    st.session_state["quick_food"] = None
    st.session_state["amount"] = "×1"


def on_manual_add():
    name = st.session_state["m_name"].strip() or "食事"
    kcal = st.session_state["m_kcal"] or 0
    protein = st.session_state["m_protein"] or 0
    if kcal == 0 and protein == 0:
        st.session_state["toast"] = "⚠️ カロリーかタンパク質を入力してください"
        return
    add_entry(st.session_state["log_date"], st.session_state["meal"] or default_meal(), name, kcal, protein)
    if st.session_state["m_save"] and st.session_state["m_name"].strip():
        my = load_csv(MY_FOODS_FILE, FOOD_COLUMNS)
        my = my[my["食品名"] != name]
        my = pd.concat([pd.DataFrame([{"食品名": name, "カロリー(kcal)": round(kcal),
                                       "タンパク質(g)": round(protein, 1)}]), my], ignore_index=True)
        save_csv(my, MY_FOODS_FILE)
    st.session_state["m_name"] = ""
    st.session_state["m_kcal"] = None
    st.session_state["m_protein"] = None
    st.session_state["m_save"] = False


# ---------- 画面 ----------
st.set_page_config(page_title="食事管理", page_icon="🍚", layout="centered")
st.markdown(
    """<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
    [data-testid="stMetricValue"] {font-size: 1.6rem;}
    .summary {display: flex; gap: 0.6rem; margin-bottom: 0.4rem;}
    .card {flex: 1; padding: 0.7rem 0.8rem; border-radius: 0.8rem; background: rgba(128,128,128,0.08);}
    .card .label {font-size: 0.8rem; opacity: 0.7;}
    .card .value {font-size: 1.6rem; font-weight: 700; line-height: 1.3;}
    .card .unit {font-size: 0.75rem; font-weight: 400; opacity: 0.7;}
    .card .bar {height: 8px; border-radius: 4px; background: rgba(128,128,128,0.2); margin: 0.3rem 0;}
    .card .bar div {height: 100%; border-radius: 4px;}
    .card .note {font-size: 0.8rem;}
    </style>""",
    unsafe_allow_html=True,
)

settings = load_settings()
if "toast" in st.session_state:
    st.toast(st.session_state.pop("toast"))

tab_log, tab_history, tab_settings = st.tabs(["🍽️ 記録", "📈 履歴", "⚙️ 設定"])

# ===== 記録タブ =====
with tab_log:
    log_date = st.date_input("日付", value=now().date(), key="log_date", format="YYYY/MM/DD",
                             label_visibility="collapsed")
    df = load_log()
    day = df[df["日付"] == log_date.isoformat()]
    kcal_total = float(day["カロリー(kcal)"].sum())
    protein_total = float(day["タンパク質(g)"].sum())

    kcal_left = settings["kcal"] - kcal_total
    protein_left = settings["protein"] - protein_total
    st.markdown(
        '<div class="summary">'
        + summary_card("カロリー", f"{kcal_total:,.0f}", "kcal", kcal_total / settings["kcal"], "#4c8bf5",
                       f"残り {kcal_left:,.0f}" if kcal_left >= 0 else f"⚠️ {-kcal_left:,.0f} オーバー",
                       f"/ {settings['kcal']:,}")
        + summary_card("タンパク質", f"{protein_total:.0f}", "g", protein_total / settings["protein"], "#2bb673",
                       f"あと {protein_left:.0f} g" if protein_left > 0 else "🎉 達成！",
                       f"/ {settings['protein']}")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.segmented_control("区分", MEALS, default=default_meal(), key="meal", label_visibility="collapsed")

    st.markdown("**タップで追加**")
    st.segmented_control("量", list(AMOUNTS), default="×1", key="amount", label_visibility="collapsed")
    st.pills("食品", list(all_foods()), key="quick_food", on_change=on_quick_add,
             label_visibility="collapsed")

    with st.expander("✏️ 手入力で追加"):
        st.text_input("食品名", key="m_name", placeholder="例：牛丼 並")
        m1, m2 = st.columns(2)
        m1.number_input("カロリー(kcal)", min_value=0, step=10, value=None, key="m_kcal")
        m2.number_input("タンパク質(g)", min_value=0.0, step=1.0, value=None, key="m_protein", format="%.1f")
        st.checkbox("マイ食品に登録（次回からタップで追加）", key="m_save")
        st.button("追加する", on_click=on_manual_add, type="primary", use_container_width=True)

    if not day.empty:
        st.markdown("**この日の記録**")
        for meal in MEALS:
            items = day[day["区分"] == meal]
            if items.empty:
                continue
            st.caption(f"{meal}　{items['カロリー(kcal)'].sum():,.0f} kcal / P {items['タンパク質(g)'].sum():.1f} g")
            st.dataframe(items[["食品名", "カロリー(kcal)", "タンパク質(g)"]], hide_index=True,
                         use_container_width=True)

        with st.expander("🗑️ 記録を削除"):
            options = {i: f"{r['時刻']} {r['区分']} {r['食品名']}（{r['カロリー(kcal)']}kcal）"
                       for i, r in day.iloc[::-1].iterrows()}
            target = st.selectbox("削除する記録", list(options), format_func=options.get)
            if st.button("削除する", use_container_width=True):
                save_csv(df.drop(index=target), LOG_FILE)
                st.session_state["toast"] = "🗑️ 削除しました"
                st.rerun()

# ===== 履歴タブ =====
with tab_history:
    period = st.segmented_control("期間", ["7日", "14日", "30日", "90日"], default="7日",
                                  label_visibility="collapsed") or "7日"
    days = int(period.rstrip("日"))
    today = now().date()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    df = load_log()
    daily = (df.groupby("日付")[["カロリー(kcal)", "タンパク質(g)"]].sum()
             .reindex([d.isoformat() for d in dates], fill_value=0).reset_index())
    daily["日付"] = pd.to_datetime(daily["日付"])
    recorded = daily[daily["カロリー(kcal)"] > 0]

    if recorded.empty:
        st.info("この期間の記録はまだありません。")
    else:
        a1, a2, a3 = st.columns(3)
        a1.metric("平均カロリー", f"{recorded['カロリー(kcal)'].mean():,.0f}")
        a2.metric("平均タンパク質", f"{recorded['タンパク質(g)'].mean():.0f} g")
        a3.metric("P目標達成", f"{(recorded['タンパク質(g)'] >= settings['protein']).sum()}/{len(recorded)}日")

        def chart(col, target, color, title):
            base = alt.Chart(daily).encode(
                x=alt.X("yearmonthdate(日付):O", title=None, axis=alt.Axis(format="%m/%d", labelAngle=0,
                                                                             labelOverlap=True)))
            bars = base.mark_bar(color=color, opacity=0.85).encode(
                y=alt.Y(f"{col}:Q", title=None),
                tooltip=[alt.Tooltip("日付:T", format="%m/%d"), alt.Tooltip(f"{col}:Q", format=",.0f")])
            rule = alt.Chart(pd.DataFrame({"y": [target]})).mark_rule(
                color="#e4572e", strokeDash=[6, 4], size=2).encode(y="y:Q")
            return (bars + rule).properties(title=title, height=220)

        st.altair_chart(chart("カロリー(kcal)", settings["kcal"], "#4c8bf5",
                              f"カロリー (kcal)　目標 {settings['kcal']:,}"), use_container_width=True)
        st.altair_chart(chart("タンパク質(g)", settings["protein"], "#2bb673",
                              f"タンパク質 (g)　目標 {settings['protein']}"), use_container_width=True)

        table = recorded.sort_values("日付", ascending=False).copy()
        table["日付"] = table["日付"].dt.strftime("%m/%d (%a)")
        table["カロリー(kcal)"] = table["カロリー(kcal)"].round(0).astype(int)
        table["タンパク質(g)"] = table["タンパク質(g)"].round(1)
        st.dataframe(table, hide_index=True, use_container_width=True)

# ===== 設定タブ =====
with tab_settings:
    st.subheader("🎯 1日の目標")
    with st.form("targets"):
        t1, t2 = st.columns(2)
        kcal_goal = t1.number_input("カロリー(kcal)", min_value=500, max_value=6000, step=50,
                                    value=int(settings["kcal"]))
        protein_goal = t2.number_input("タンパク質(g)", min_value=10, max_value=400, step=5,
                                       value=int(settings["protein"]))
        if st.form_submit_button("保存", use_container_width=True):
            save_settings({"kcal": kcal_goal, "protein": protein_goal})
            st.session_state["toast"] = "✅ 目標を保存しました"
            st.rerun()

    st.subheader("⭐ マイ食品")
    my = load_csv(MY_FOODS_FILE, FOOD_COLUMNS)
    st.caption("手入力時に「マイ食品に登録」した食品です。表を直接編集・行削除できます。")
    edited = st.data_editor(my, num_rows="dynamic", hide_index=True, use_container_width=True, key="my_foods")
    if st.button("マイ食品を保存", use_container_width=True):
        save_csv(edited.dropna(subset=["食品名"]), MY_FOODS_FILE)
        st.session_state["toast"] = "✅ マイ食品を保存しました"
        st.rerun()

    st.subheader("💾 バックアップ")
    log = load_log()
    st.download_button("⬇️ 記録をCSVでダウンロード", log.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                       file_name="diet_log.csv", use_container_width=True, disabled=log.empty)
    uploaded = st.file_uploader("CSVから復元（現在の記録は置き換わります）", type="csv")
    if uploaded is not None and st.button("復元する", use_container_width=True):
        restored = pd.read_csv(uploaded, encoding="utf-8-sig")
        if set(LOG_COLUMNS) <= set(restored.columns):
            save_csv(restored[LOG_COLUMNS], LOG_FILE)
            st.session_state["toast"] = "✅ 復元しました"
            st.rerun()
        else:
            st.error("このアプリの記録CSVではありません。")
