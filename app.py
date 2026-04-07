import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime, date

st.set_page_config(page_title="ホットライン受付対応表", layout="centered")
st.title("📞 ホットライン受付対応表")

# ===== フォント =====
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

def get_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def getlength(text, font):
    bb = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), text, font=font)
    return bb[2] - bb[0]

def draw_maru(draw, center, r=14):
    x, y = center
    draw.ellipse([x-r, y-r, x+r, y+r], outline="black", width=3)

# ===== 救急隊リスト =====
RESCUE_TEAMS = [
    "", "中央","大通","桑園","山鼻","北","篠路","新光","東","栄","東苗穂",
    "白石","菊水","厚別","厚別西","豊平","西岡","平岸","清田","南","定山渓",
    "西","前田","西野","手稲","石山","あいの里","北野","警防","豊水","幌西",
    "藤野","八軒","北郷","札苗","苗穂","北エルム","東モエレ",
]

LEADERS = ["前川","中嶋","森木","小舘","遠藤"]

WEEKDAYS = ["月","火","水","木","金","土","日"]

# ===== テンプレート定数 =====
# 画像サイズ: 1413x2000
# ヘッダー: Y=0-168
# 各ブロック境界 Y: 168,460,749,1039,1329,1619,1911
BLOCK_TOPS = [168, 460, 749, 1039, 1329, 1619]
BLOCK_H = [292, 289, 290, 290, 290, 292]  # 各ブロック高さ

# ブロック内相対Y（ブロック高さ292基準）
# No.行: rel_y=0 (絶対 y_start)
# 症例行: rel_y≈118
# 転帰行: rel_y≈219
# お断り理由行: rel_y≈268

# ===== 描画関数 =====
def render_hotline(header, cases):
    base = Image.open("hotline.png").convert("RGB")
    d = ImageDraw.Draw(base)

    f16 = get_font(16)
    f18 = get_font(18)
    f20 = get_font(20)
    f22 = get_font(22)
    f26 = get_font(26)

    # ===== ヘッダー =====
    # 年月日 (Y≈130)
    dt = header["date"]
    wd = WEEKDAYS[dt.weekday()]
    d.text((245, 122), str(dt.year), font=f20, fill="black")
    d.text((410, 122), str(dt.month), font=f20, fill="black")
    d.text((530, 122), str(dt.day), font=f20, fill="black")
    d.text((625, 122), wd, font=f20, fill="black")

    # 日勤・夜勤
    # 日勤◯中心: X≈795, 夜勤◯中心: X≈878  Y≈138
    if header["shift"] == "日勤":
        draw_maru(d, (797, 138), r=16)
    else:
        draw_maru(d, (878, 138), r=16)

    # リーダー医師名
    d.text((1010, 125), header["leader"], font=f22, fill="black")

    # ===== 各症例ブロック =====
    for i, case in enumerate(cases):
        if i >= 6:
            break
        yt = BLOCK_TOPS[i]    # ブロック上端Y

        # --- No. + 時刻行 (yt + 0) ---
        y_no = yt + 20

        # 時刻
        if case["time"]:
            d.text((220, y_no), case["time"], font=f22, fill="black")

        # 依頼回数
        if case["req_count"] and case["req_count"] != "初回":
            d.text((540, y_no), case["req_count"], font=f20, fill="black")
        else:
            # 初回に○
            draw_maru(d, (540, y_no + 10), r=12)

        # 依頼先（救急隊名）
        if case["team"]:
            d.text((900, y_no), case["team"], font=f22, fill="black")

        # --- 症例行 (yt + 118) ---
        y_case = yt + 118 + 15

        # 年齢
        if case["age"]:
            d.text((196, y_case), str(case["age"]), font=f20, fill="black")

        # 性別 M/F
        # M位置 X≈490, F位置 X≈555
        if case["gender"] == "M":
            draw_maru(d, (490, y_case + 8), r=14)
        elif case["gender"] == "F":
            draw_maru(d, (555, y_case + 8), r=14)

        # 概略（折返し幅50文字）
        y_ryaku = yt + 118 + 50
        summary = case["summary"]
        lines = []
        line = ""
        for ch in summary:
            line += ch
            if len(line) >= 45:
                lines.append(line)
                line = ""
        if line:
            lines.append(line)
        for li, ln in enumerate(lines[:2]):
            d.text((130, y_ryaku + li * 28), ln, font=f18, fill="black")

        # --- 転帰行 (yt + 219) ---
        y_tenki = yt + 219 + 18

        # 転帰チェックボックス位置（□の中心）
        # 搬入 X≈162, お断り X≈325, 2次やかかりつけ X≈750, 患者都合 X≈975
        # その他(下段) X≈213
        tenki_map = {
            "搬入":           (162, y_tenki),
            "お断り":         (325, y_tenki),
            "2次やかかりつけ医案内": (750, y_tenki),
            "患者都合":       (975, y_tenki),
            "その他":         (213, y_tenki + 45),
        }
        if case["outcome"] in tenki_map:
            cx, cy = tenki_map[case["outcome"]]
            draw_maru(d, (cx, cy), r=13)

        # --- お断り理由行 (yt + 268) ---
        y_kotowari = yt + 268

        if case["outcome"] == "お断り":
            reason = case.get("reason", "")

            # 理由1: 病床 X≈140
            if reason == "1_満床":
                draw_maru(d, (140, y_kotowari + 15), r=11)
                # サブ選択
                sub_map = {
                    "満床": (265, y_kotowari + 15),
                    "満床に準ずる状態": (390, y_kotowari + 15),
                    "ICU個室(感染等)満床": (575, y_kotowari + 15),
                    "熱傷患者受入不能": (790, y_kotowari + 15),
                }
                sub = case.get("reason1_sub", "")
                if sub in sub_map:
                    draw_maru(d, sub_map[sub], r=10)

            # 理由2: マンパワー
            elif reason == "2_マンパワー":
                draw_maru(d, (140, y_kotowari + 38), r=11)
                sub_map2 = {
                    "他患の処置・手術等で余力なし": (360, y_kotowari + 38),
                    "別の救急患者の搬入直前・直後": (620, y_kotowari + 38),
                }
                sub = case.get("reason2_sub", "")
                if sub in sub_map2:
                    draw_maru(d, sub_map2[sub], r=10)

            # 理由3: 院内専門科
            elif reason == "3_院内専門科":
                draw_maru(d, (140, y_kotowari + 60), r=11)
                # 科名
                if case.get("reason3_dept"):
                    d.text((310, y_kotowari + 50), case["reason3_dept"].rstrip("科"), font=f16, fill="black")
                # サブ
                sub_map3 = {
                    "当該科手術中": (580, y_kotowari + 60),
                    "学会等で不在": (730, y_kotowari + 60),
                    "麻酔科対応不能": (875, y_kotowari + 60),
                }
                sub = case.get("reason3_sub", "")
                if sub in sub_map3:
                    draw_maru(d, sub_map3[sub], r=10)

    return base

# ===== UI =====

# ヘッダー入力
st.subheader("📋 基本情報")
col1, col2, col3 = st.columns(3)
with col1:
    input_date = st.date_input("日付", value=date.today())
with col2:
    shift = st.radio("勤務帯", ["日勤", "夜勤"], horizontal=True)
with col3:
    leader = st.selectbox("リーダー医師名", LEADERS)

header = {"date": input_date, "shift": shift, "leader": leader}

st.divider()

# 症例入力（最大6件）
st.subheader("🚑 症例入力")
n_cases = st.number_input("症例数", min_value=1, max_value=6, value=1, step=1)

cases = []
for i in range(int(n_cases)):
    with st.expander(f"症例 {i+1}", expanded=(i == 0)):
        c1, c2 = st.columns(2)
        with c1:
            time_val = st.text_input("時刻 (HH:MM)", key=f"time_{i}", placeholder="22:50")
            team = st.selectbox("依頼先救急隊", RESCUE_TEAMS, key=f"team_{i}")
        with c2:
            req_count = st.selectbox("依頼回数", ["初回", "2回目", "3回目", "4回目以上"], key=f"req_{i}")
            gender = st.radio("性別", ["M", "F", "未記載"], horizontal=True, key=f"gender_{i}")

        age = st.number_input("年齢（才）", min_value=0, max_value=120, value=0, step=1, key=f"age_{i}")
        summary = st.text_area("概略", key=f"summary_{i}", height=70, placeholder="主訴・概略を入力")

        outcome = st.radio(
            "転帰",
            ["搬入", "お断り", "2次やかかりつけ医案内", "患者都合", "その他"],
            horizontal=True,
            key=f"outcome_{i}"
        )

        case = {
            "time": time_val,
            "team": team,
            "req_count": req_count,
            "age": age if age > 0 else "",
            "gender": gender if gender != "未記載" else "",
            "summary": summary,
            "outcome": outcome,
        }

        if outcome == "お断り":
            reason = st.radio(
                "お断り理由",
                ["1_満床", "2_マンパワー", "3_院内専門科"],
                format_func=lambda x: {
                    "1_満床": "1. 病床の都合がつかない",
                    "2_マンパワー": "2. マンパワーの問題",
                    "3_院内専門科": "3. 院内専門科の都合・体制"
                }[x],
                key=f"reason_{i}"
            )
            case["reason"] = reason

            if reason == "1_満床":
                sub1 = st.selectbox(
                    "病床理由の詳細",
                    ["", "満床", "満床に準ずる状態", "ICU個室(感染等)満床", "熱傷患者受入不能"],
                    key=f"r1sub_{i}"
                )
                case["reason1_sub"] = sub1

            elif reason == "2_マンパワー":
                sub2 = st.selectbox(
                    "マンパワー理由の詳細",
                    ["", "他患の処置・手術等で余力なし", "別の救急患者の搬入直前・直後"],
                    key=f"r2sub_{i}"
                )
                case["reason2_sub"] = sub2

            elif reason == "3_院内専門科":
                dept3 = st.text_input("専門科名", key=f"dept3_{i}", placeholder="循環器")
                sub3 = st.selectbox(
                    "専門科理由の詳細",
                    ["", "当該科手術中", "学会等で不在", "麻酔科対応不能"],
                    key=f"r3sub_{i}"
                )
                case["reason3_dept"] = dept3
                case["reason3_sub"] = sub3

        cases.append(case)

st.divider()

if st.button("🖨️ 受付対応表を生成", type="primary", use_container_width=True):
    with st.spinner("生成中..."):
        result = render_hotline(header, cases)
    st.image(result, use_container_width=True)
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    fname = f"hotline_{input_date.strftime('%Y%m%d')}_{shift}.jpg"
    st.download_button("📥 保存", buf.getvalue(), fname, "image/jpeg")
