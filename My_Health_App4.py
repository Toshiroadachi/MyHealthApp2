import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.font_manager as fm

FONT_PATH = "ipaexg.ttf"
LOG_FILE = "bmi_log.csv"
GRAPH_PATH = "bmi_graph.png"

# ログ読み込み
def load_log():
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
        for col in ["ランニング(km)", "自転車(km)", "水泳(km)"]:
            if col not in df.columns:
                df[col] = 0.0
        return df
    else:
        return pd.DataFrame(columns=[
            "日時", "身長(m)", "体重(kg)", "腹囲(cm)", "BMI", "性別",
            "ランニング(km)", "自転車(km)", "水泳(km)"
        ])

# ログ保存
def save_log(entry):
    df = load_log()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")

# グラフ生成（日本語対応）
def generate_bmi_plot(df):
    df_plot = df.tail(10).copy()
    df_plot["日時"] = pd.to_datetime(df_plot["日時"])
    font_prop = fm.FontProperties(fname=FONT_PATH)
    rcParams['font.family'] = font_prop.get_name()

    fig, ax = plt.subplots()
    ax.plot(df_plot["日時"], df_plot["体重(kg)"], marker='o', label='体重 (kg)')
    ax.set_title("体重の推移", fontsize=14)
    ax.set_xlabel("日付", fontsize=12)
    ax.set_ylabel("体重 (kg)", fontsize=12)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    fig.savefig(GRAPH_PATH)
    return GRAPH_PATH

# Streamlit画面設定
st.set_page_config(page_title="健康チェックアプリ", layout="centered")
st.title("📱 健康チェックアプリ（診断・PDF対応）")

# 入力フォーム
with st.form("health_form"):
    st.subheader("📥 毎日の健康データ入力")
    st.info("🔒 身長は固定: **1.73 m**")
    height = 1.73

    weight = st.number_input("体重 (kg)", value=66.0, step=0.1)
    waist = st.number_input("腹囲 (cm)", value=83.0, step=0.1)
    gender = st.radio("性別", ["男性", "女性"], horizontal=True)

    run = st.number_input("🏃‍♀️ ランニング距離 (km)", min_value=0.0, step=0.1)
    bike = st.number_input("🚴‍♂️ 自転車距離 (km)", min_value=0.0, step=0.1)
    swim = st.number_input("🏊 水泳距離 (km)", min_value=0.0, step=0.1)

    submitted = st.form_submit_button("✅ 診断・保存")

# 診断・保存
if submitted:
    bmi = weight / (height ** 2)
    ideal_weight = 22 * (height ** 2)

    # 判定ロジック
    bmi_msg = "やせ型" if bmi < 18.5 else "標準体型" if bmi < 25 else "肥満（1度）" if bmi < 30 else "高度肥満"
    waist_msg = "正常" if (waist < 85 if gender == "男性" else waist < 90) else "メタボの可能性あり"
    diff = weight - ideal_weight
    weight_msg = "標準体型" if abs(diff) <= ideal_weight * 0.1 else "やせ型" if weight < ideal_weight else "太り気味"

    # 結果表示
    st.subheader("📊 診断結果")
    st.write(f"適正体重: **{ideal_weight:.2f} kg**")
    st.write(f"BMI: **{bmi:.2f}**")
    st.write(f"体重判定: **{weight_msg}**")
    st.write(f"BMI判定: **{bmi_msg}**")
    st.write(f"腹囲判定: **{waist_msg}**")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_entry = {
        "日時": now, "身長(m)": height, "体重(kg)": weight, "腹囲(cm)": waist,
        "BMI": round(bmi, 2), "性別": gender,
        "ランニング(km)": run, "自転車(km)": bike, "水泳(km)": swim
    }
    save_log(log_entry)
    st.success("✅ ログを保存しました。")

# ログ・PDF出力
df = load_log()
if not df.empty:
    st.subheader("📒 最近の記録")
    st.dataframe(df.tail(10), use_container_width=True)
    st.download_button("⬇️ CSVダウンロード", df.to_csv(index=False, encoding="utf-8-sig").encode(), file_name="bmi_log.csv")

    st.subheader("📄 PDF診断書")
    if st.button("📤 PDFを生成"):
        latest = df.iloc[-1]
        weight = latest["体重(kg)"]
        waist = latest["腹囲(cm)"]
        height = latest["身長(m)"]
        bmi = latest["BMI"]
        gender = latest["性別"]
        ideal_weight = 22 * (height ** 2)

        # 再判定（確実性のため）
        bmi_msg = "やせ型" if bmi < 18.5 else "標準体型" if bmi < 25 else "肥満（1度）" if bmi < 30 else "高度肥満"
        waist_msg = "正常" if (waist < 85 if gender == "男性" else waist < 90) else "メタボの可能性あり"
        diff = weight - ideal_weight
        weight_msg = "標準体型" if abs(diff) <= ideal_weight * 0.1 else "やせ型" if weight < ideal_weight else "太り気味"

        generate_bmi_plot(df)
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("IPAexGothic", '', FONT_PATH, uni=True)
        pdf.set_font("IPAexGothic", '', 12)
        pdf.cell(200, 10, txt="健康診断書", ln=1, align="C")

        for k, v in latest.items():
            pdf.cell(0, 10, txt=f"{k}: {v}", ln=1)

        pdf.cell(0, 10, txt=f"体重判定: {weight_msg}", ln=1)
        pdf.cell(0, 10, txt=f"BMI判定: {bmi_msg}", ln=1)
        pdf.cell(0, 10, txt=f"腹囲判定: {waist_msg}", ln=1)
        pdf.image(GRAPH_PATH, x=10, y=None, w=180)
        pdf.output("bmi_report.pdf")

        with open("bmi_report.pdf", "rb") as f:
            st.download_button("📥 PDFダウンロード", f, file_name="bmi_report.pdf")
else:
    st.info("まだ記録がありません。")
