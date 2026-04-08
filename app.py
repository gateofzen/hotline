import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import date

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

def draw_maru(draw, center, r=14):
    x, y = center
    draw.ellipse([x-r, y-r, x+r, y+r], outline="black", width=4)

# ===== 定数 =====
RESCUE_TEAMS = [
    "","中央","大通","桑園","山鼻","北","篠路","新光","東","栄","東苗穂",
    "白石","菊水","厚別","厚別西","豊平","西岡","平岸","清田","南","定山渓",
    "西","前田","西野","手稲","石山","あいの里","北野","警防","豊水","幌西",
    "藤野","八軒","北郷","札苗","苗穂","北エルム","東モエレ",
]
LEADERS = ["前川","中嶋","森木","小舘","遠藤"]
WEEKDAYS = ["月","火","水","木","金","土","日"]
BLOCK_TOPS = [168, 460, 749, 1039, 1329, 1619]

# ===== 描画 =====
def render_hotline(header, cases):
    base = Image.open("hotline.png").convert("RGB")
    d = ImageDraw.Draw(base)
    f24 = get_font(24)
    f26 = get_font(26)
    f28 = get_font(28)

    # ヘッダー
    dt = header["date"]
    wd = WEEKDAYS[dt.weekday()]
    d.text((330, 122), str(dt.year), font=f26, fill="black")
    d.text((430, 122), str(dt.month), font=f26, fill="black")
    d.text((520, 122), str(dt.day), font=f26, fill="black")
    d.text((608, 122), wd, font=f26, fill="black")

    # 日勤(X=549) / 夜勤(X=693)
    if header["shift"] == "日勤":
        draw_maru(d, (549, 139), r=18)
    else:
        draw_maru(d, (693, 139), r=18)

    d.text((1010, 122), header["leader"], font=f28, fill="black")

    for i, case in enumerate(cases):
        if i >= 6:
            break
        yt = BLOCK_TOPS[i]
        yn = yt + 16   # No.行テキストY

        # 時刻（":"はテンプレート印刷済み → 左に時、右に分）
        if case.get("hour"):
            d.text((222, yn), case["hour"], font=f28, fill="black")
        if case.get("minute"):
            d.text((285, yn), case["minute"], font=f28, fill="black")

        # 依頼回数（初回◯ or 数字）
        if case.get("req_count") == "初回":
            draw_maru(d, (635, yn+10), r=16)
        else:
            num = case.get("req_count","").replace("回目","").replace("回","")
            if num:
                d.text((730, yn), num, font=f28, fill="black")

        # 依頼先
        if case.get("team"):
            d.text((930, yn), case["team"], font=f28, fill="black")

        # 症例行
        yc = yt + 52
        if case.get("age"):
            d.text((290, yc), str(case["age"]), font=f28, fill="black")
        if case.get("gender") == "M":
            draw_maru(d, (490, yc+10), r=16)
        elif case.get("gender") == "F":
            draw_maru(d, (570, yc+10), r=16)

        # 概略
        yg = yt + 100
        lines = []
        line = ""
        for ch in (case.get("summary") or ""):
            line += ch
            if len(line) >= 38:
                lines.append(line); line = ""
        if line:
            lines.append(line)
        for li, ln in enumerate(lines[:3]):
            d.text((160, yg + li*32), ln, font=f26, fill="black")

        # 転帰行
        yt2 = yt + 219
        yn2 = yt2 + 16
        tenki_map = {
            "搬入":               (162, yn2),
            "お断り":             (347, yn2),
            "2次やかかりつけ医案内": (644, yn2),
            "患者都合":           (801, yn2),
            "その他":             (175, yn2+45),
        }
        outcome = case.get("outcome","")
        if outcome in tenki_map:
            draw_maru(d, tenki_map[outcome], r=15)

        # お断り理由行
        yr = yt + 268
        yr1, yr2, yr3 = yr+15, yr+38, yr+62

        if outcome == "お断り":
            reason = case.get("reason","")
            if reason == "1_満床":
                draw_maru(d, (140, yr1), r=12)
                sub_map = {
                    "満床": (265,yr1), "満床に準ずる状態": (405,yr1),
                    "ICU個室(感染等)満床": (600,yr1), "熱傷患者受入不能": (815,yr1),
                }
                if case.get("reason1_sub") in sub_map:
                    draw_maru(d, sub_map[case["reason1_sub"]], r=11)
            elif reason == "2_マンパワー":
                draw_maru(d, (140, yr2), r=12)
                sub_map2 = {
                    "他患の処置・手術等で余力なし": (400,yr2),
                    "別の救急患者の搬入直前・直後": (660,yr2),
                }
                if case.get("reason2_sub") in sub_map2:
                    draw_maru(d, sub_map2[case["reason2_sub"]], r=11)
            elif reason == "3_院内専門科":
                draw_maru(d, (140, yr3), r=12)
                if case.get("reason3_dept"):
                    d.text((325, yr3-12), case["reason3_dept"].rstrip("科"), font=f24, fill="black")
                sub_map3 = {
                    "当該科手術中": (595,yr3), "学会等で不在": (750,yr3),
                    "麻酔科対応不能": (905,yr3),
                }
                if case.get("reason3_sub") in sub_map3:
                    draw_maru(d, sub_map3[case["reason3_sub"]], r=11)
    return base

# ===== セッション状態 =====
if "hl_cases" not in st.session_state:
    st.session_state.hl_cases = []
if "hl_header" not in st.session_state:
    st.session_state.hl_header = {"date": date.today(), "shift": "日勤", "leader": "前川"}

# ===== ヘッダー =====
st.subheader("📋 基本情報")
c1, c2, c3 = st.columns(3)
with c1:
    input_date = st.date_input("日付", value=st.session_state.hl_header["date"])
with c2:
    shift = st.radio("勤務帯", ["日勤","夜勤"], horizontal=True,
                     index=0 if st.session_state.hl_header["shift"]=="日勤" else 1)
with c3:
    leader = st.selectbox("リーダー医師名", LEADERS,
                          index=LEADERS.index(st.session_state.hl_header["leader"]))
st.session_state.hl_header = {"date": input_date, "shift": shift, "leader": leader}

# ===== 症例リスト =====
st.divider()
n = len(st.session_state.hl_cases)
st.subheader(f"🚑 登録済み症例: {n}件 / 6件")

for i, c in enumerate(st.session_state.hl_cases):
    team_str = c.get("team","") or "隊名なし"
    h = c.get("hour","?"); m = c.get("minute","?")
    outcome_str = c.get("outcome","")
    col_a, col_b = st.columns([6,1])
    with col_a:
        st.write(f"**症例{i+1}**　{h}:{m}　{team_str}救急隊　→ {outcome_str}")
    with col_b:
        if st.button("削除", key=f"del_{i}"):
            st.session_state.hl_cases.pop(i)
            st.rerun()

# ===== 新規入力 =====
if n < 6:
    st.divider()
    st.subheader(f"➕ 症例 {n+1} を入力")

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        hour = st.text_input("時（HH）", max_chars=2, placeholder="22")
    with cc2:
        minute = st.text_input("分（MM）", max_chars=2, placeholder="50")
    with cc3:
        team = st.selectbox("依頼先救急隊", RESCUE_TEAMS)

    cc4, cc5, cc6 = st.columns(3)
    with cc4:
        req_count = st.selectbox("依頼回数", ["初回","2回目","3回目","4回目以上"])
    with cc5:
        age = st.number_input("年齢（才）", min_value=0, max_value=120, value=0, step=1)
    with cc6:
        gender = st.radio("性別", ["M","F","未記載"], horizontal=True)

    summary = st.text_area("概略", height=70, placeholder="主訴・経過を入力")
    outcome = st.radio("転帰", ["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"], horizontal=True)

    reason = reason1_sub = reason2_sub = reason3_dept = reason3_sub = ""
    if outcome == "お断り":
        reason = st.radio("お断り理由",
            ["1_満床","2_マンパワー","3_院内専門科"],
            format_func=lambda x: {"1_満床":"1. 病床の都合","2_マンパワー":"2. マンパワーの問題","3_院内専門科":"3. 院内専門科の都合"}[x]
        )
        if reason == "1_満床":
            reason1_sub = st.selectbox("病床理由詳細", ["","満床","満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"])
        elif reason == "2_マンパワー":
            reason2_sub = st.selectbox("マンパワー理由詳細", ["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"])
        elif reason == "3_院内専門科":
            reason3_dept = st.text_input("専門科名", placeholder="循環器")
            reason3_sub = st.selectbox("専門科理由詳細", ["","当該科手術中","学会等で不在","麻酔科対応不能"])

    if st.button("✅ この症例を登録", type="primary", use_container_width=True):
        st.session_state.hl_cases.append({
            "hour": hour, "minute": minute, "team": team,
            "req_count": req_count,
            "age": age if age > 0 else "",
            "gender": gender if gender != "未記載" else "",
            "summary": summary, "outcome": outcome,
            "reason": reason, "reason1_sub": reason1_sub,
            "reason2_sub": reason2_sub, "reason3_dept": reason3_dept,
            "reason3_sub": reason3_sub,
        })
        st.rerun()
else:
    st.info("6件登録済み（1枚の上限）。")

# ===== 出力 =====
st.divider()
col_out1, col_out2 = st.columns(2)
with col_out1:
    if st.button("🖨️ 受付対応表を生成", type="primary", use_container_width=True,
                 disabled=(len(st.session_state.hl_cases)==0)):
        with st.spinner("生成中..."):
            result = render_hotline(st.session_state.hl_header, st.session_state.hl_cases)
        st.image(result, use_container_width=True)
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=95)
        fname = f"hotline_{input_date.strftime('%Y%m%d')}_{shift}.jpg"
        st.download_button("📥 保存", buf.getvalue(), fname, "image/jpeg")
with col_out2:
    if st.button("🗑️ 全症例をリセット", use_container_width=True):
        st.session_state.hl_cases = []
        st.rerun()
