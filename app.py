import streamlit as st
import swisseph as swe
import pandas as pd
from datetime import datetime, time # datetimeクラスとtimeクラスを直接ロード
import os
import re

# --- 1. ブランド・基本設定 ---
st.set_page_config(page_title="澄結 (Sumiyui) - Destiny Redesign", layout="wide")
st.title("澄結 (Sumiyui) : 運命再設計ツール")

# --- 2. 重要軸（ハーフサム）の定義 ---
IMPORTANT_AXES = {
    ("Sun", "Jupiter"): "成功軸: 社会的発展のトリガー",
    ("Venus", "Jupiter"): "幸福軸: 感情的充足と豊かさ",
    ("Sun", "Moon"): "家庭・結婚軸: 公私の統合点",
    ("Mars", "Jupiter"): "飛躍軸: 実行力と拡大の結びつき",
    ("Saturn", "Pluto"): "忍耐軸: 根本的な再構築のデバッグ",
    ("Jupiter", "Uranus"): "開運軸: 突然のシステム更新",
    ("Sun", "ASC"): "健康・自己表現軸: 生命力のデバッグ",
    ("MC", "Jupiter"): "社会・成功軸: キャリアの最大チャンス",
}

# --- 3. データロード (sabian.csv) ---
@st.cache_data
def load_sabian():
    file_path = "sabian.csv"
    if not os.path.exists(file_path):
        return {i: f"Degree {i} Symbol" for i in range(1, 361)}
    
    try:
        # エンコーディング対応
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except:
            df = pd.read_csv(file_path, encoding="shift-jis")
        
        df.columns = [c.lower() for c in df.columns]
        converted_dict = {}
        for _, row in df.iterrows():
            d = int(row['degree'])
            s = str(row['symbol'])
            m = str(row['meaning']) if 'meaning' in df.columns else ""
            converted_dict[d] = f"【{s}】 {m}"
        return converted_dict
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        return {i: f"Degree {i} Symbol" for i in range(1, 361)}

sabian_dict = load_sabian()

# --- 4. ロジック関数 ---
def get_sabian_degree(degree):
    """0-359.99を1-360の数え度数へ変換"""
    return int(degree % 360) + 1

def calculate_midpoint(p1, p2):
    """最短弧の中点算出"""
    diff = abs(p1 - p2)
    mid = (p1 + p2) / 2 if diff <= 180 else (p1 + p2) / 2 + 180
    return mid % 360

# --- 5. サイドバー：入力 ---
with st.sidebar:
    st.header("出生データ入力")
    b_date = st.date_input("生年月日", datetime(1980, 1, 1))
    b_time = st.time_input("出生時間", time(12, 0))
    lat = st.number_input("緯度", value=35.6895, format="%.4f")
    lon = st.number_input("経度", value=139.6917, format="%.4f")
    tz = st.number_input("時差 (JST=9)", value=9.0)
    st.info("※猫ちゃんの世話（割り込み処理）の合間にデバッグしてください。")

# --- 6. 計算実行 ---
# datetime.combineを使用するためにfrom datetime import datetimeが必要
dt_combined = datetime.combine(b_date, b_time)
jd_utc = swe.julday(dt_combined.year, dt_combined.month, dt_combined.day, 
                    dt_combined.hour + dt_combined.minute/60 - tz)

# 天体計算
bodies = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO
}
positions = {name: swe.calc_ut(jd_utc, id)[0][0] for name, id in bodies.items()}

# ASC / MC 計算 (プラシーダス)
res_houses = swe.houses_ex(jd_utc, lat, lon, b'P')
positions["ASC"] = res_houses[1][0]
positions["MC"] = res_houses[1][1]

# --- 7. 結果表示 ---

# A. ネイタル天体位置 & HN8位置
st.subheader("🪐 天体・感受点データ (Natal & HN8)")
natal_hn_data = []
for name, deg in positions.items():
    s_deg = get_sabian_degree(deg)
    # 第8調波（HN8）の計算
    hn8_deg = (deg * 8) % 360
    h8_s_deg = get_sabian_degree(hn8_deg)
    
    natal_hn_data.append({
        "ポイント": name,
        "N度数": round(deg, 2),
        "Nサビアン": sabian_dict.get(s_deg, f"Degree {s_deg}"),
        "HN8度数": round(hn8_deg, 2),
        "HN8サビアン": sabian_dict.get(h8_s_deg, f"Degree {h8_s_deg}")
    })
st.dataframe(pd.DataFrame(natal_hn_data), use_container_width=True)

# B. 推奨デバッグ項目（重要軸）
st.subheader("🛠 推奨デバッグ項目（重要軸）")
important_results = []
all_results = []
planets = list(positions.keys())

for i in range(len(planets)):
    for j in range(i + 1, len(planets)):
        p1, p2 = planets[i], planets[j]
        mid = calculate_midpoint(positions[p1], positions[p2])
        # ハーフサムの中点に対するHN8の算出
        hn8_mid = (mid * 8) % 360
        
        s_deg = get_sabian_degree(mid)
        h_deg = get_sabian_degree(hn8_mid)
        
        data = {
            "Combination": f"{p1} / {p2}",
            "Midpoint": round(mid, 2),
            "Sabian": sabian_dict.get(s_deg, f"Degree {s_deg}"),
            "HN8_Midpoint": round(hn8_mid, 2),
            "HN8_Sabian": sabian_dict.get(h_deg, f"Degree {h_deg}")
        }

        # 重要軸判定
        pair = tuple(sorted((p1, p2)))
        key_matches = [k for k in IMPORTANT_AXES.keys() if tuple(sorted(k)) == pair]
        if key_matches:
            data["Meaning"] = IMPORTANT_AXES[key_matches[0]]
            important_results.append(data)
        all_results.append(data)

if important_results:
    st.table(pd.DataFrame(important_results)[["Combination", "Meaning", "Sabian", "HN8_Sabian"]])

with st.expander("全ハーフサム・デバッグデータ"):
    df_all = pd.DataFrame(all_results)
    st.dataframe(df_all, use_container_width=True)
    csv = df_all.to_csv(index=False).encode('utf-8')
    st.download_button("CSV Export", data=csv, file_name="sumiyui_all_data.csv")