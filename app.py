import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os
from datetime import date

st.set_page_config(page_title="ホットライン受付対応表", layout="centered")
st.title("📞 ホットライン受付対応表")

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
def get_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_maru(draw, cx, cy, r=14):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="black", width=4)

RESCUE_TEAMS = [
    "","中央","大通","桑園","山鼻","北","篠路","新光","東","栄","東苗穂",
    "白石","菊水","厚別","厚別西","豊平","西岡","平岸","清田","南","定山渓",
    "西","前田","西野","手稲","石山","あいの里","北野","警防","豊水","幌西",
    "藤野","八軒","北郷","札苗","苗穂","北エルム","東モエレ",
]
LEADERS   = ["前川","中嶋","森木","小舘","遠藤"]
WEEKDAYS  = ["月","火","水","木","金","土","日"]
BLOCK_TOPS = [168, 460, 749, 1039, 1329, 1619]
TIME_OPTIONS = [""] + [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0,60,5)]

def render_hotline(header, cases):
    base = Image.open("hotline.png").convert("RGB")
    d = ImageDraw.Draw(base)
    f36 = get_font(36)
    f32 = get_font(32)
    f28 = get_font(28)
    f26 = get_font(26)

    # ===== ヘッダー =====
    dt = header["date"]
    wd = WEEKDAYS[dt.weekday()]
    d.text((280, 108), str(dt.year), font=f32, fill="black")
    d.text((420, 108), str(dt.month), font=f32, fill="black")
    d.text((485, 108), str(dt.day), font=f32, fill="black")
    d.text((590, 108), wd, font=f32, fill="black")
    # 日勤X=701 / 夜勤X=778（テンプレート解析済み）
    if header["shift"] == "日勤":
        draw_maru(d, 701, 138, r=18)
    else:
        draw_maru(d, 778, 138, r=18)
    d.text((1080, 108), header["leader"], font=f36, fill="black")

    # ===== 症例ブロック =====
    for i, case in enumerate(cases):
        if i >= 6: break
        yt  = BLOCK_TOPS[i]
        yn  = yt - 8     # 時刻/救急隊名行（確認済み）
        yc  = yt + 22    # 症例行（確認済み）
        yg  = yt + 60    # 概略
        yn2 = yt + 131   # 転帰行
        yr1 = yt + 240   # 理由1 Y
        yr2 = yt + 260   # 理由2 Y
        yr3 = yt + 280   # 理由3 Y

        # 時刻
        if case.get("time"):
            d.text((295, yn), case["time"], font=f32, fill="black")

        # 依頼回数
        if case.get("req_count") == "初回":
            draw_maru(d, 620, yn+14, r=16)
        else:
            num = (case.get("req_count") or "").replace("回目","").replace("回","")
            if num:
                d.text((718, yn), num, font=f32, fill="black")

        # 依頼先
        if case.get("team"):
            d.text((970, yn), case["team"], font=f32, fill="black")

        # 年齢
        if case.get("age"):
            d.text((235, yc), str(case["age"]), font=f32, fill="black")

        # 性別（確認済み: M X=505, F X=548, Y=yc+22）
        if case.get("gender") == "M":
            draw_maru(d, 505, yc+22, r=16)
        elif case.get("gender") == "F":
            draw_maru(d, 548, yc+22, r=16)

        # 概略（折返し幅32文字）
        lines = []
        line = ""
        for ch in (case.get("summary") or ""):
            line += ch
            if len(line) >= 32: lines.append(line); line = ""
        if line: lines.append(line)
        for li, ln in enumerate(lines[:2]):
            d.text((168, yg + li*30), ln, font=f26, fill="black")

        # 転帰
        outcome = case.get("outcome","")
        tenki_map = {
            "搬入":               (195, yn2),
            "お断り":             (270, yn2),
            "2次やかかりつけ医案内": (500, yn2),
            "患者都合":           (790, yn2),
            "その他":             (192, yt+214),
        }
        if outcome in tenki_map:
            draw_maru(d, *tenki_map[outcome], r=14)

        # お断り理由
        if outcome == "お断り":
            reason = case.get("reason","")
            if reason == "1_満床":
                draw_maru(d, 215, yr1, r=12)
                sub_map = {
                    "満床": (263,yr1), "満床に準ずる状態": (405,yr1),
                    "ICU個室(感染等)満床": (600,yr1), "熱傷患者受入不能": (815,yr1),
                }
                if case.get("reason1_sub") in sub_map:
                    draw_maru(d, *sub_map[case["reason1_sub"]], r=11)
            elif reason == "2_マンパワー":
                draw_maru(d, 215, yr2, r=12)
                sub_map2 = {
                    "他患の処置・手術等で余力なし": (398,yr2),
                    "別の救急患者の搬入直前・直後": (658,yr2),
                }
                if case.get("reason2_sub") in sub_map2:
                    draw_maru(d, *sub_map2[case["reason2_sub"]], r=11)
            elif reason == "3_院内専門科":
                draw_maru(d, 215, yr3, r=12)
                if case.get("reason3_dept"):
                    d.text((328, yr3-14), case["reason3_dept"].rstrip("科"), font=f28, fill="black")
                sub_map3 = {
                    "当該科手術中": (597,yr3), "学会等で不在": (752,yr3),
                    "麻酔科対応不能": (907,yr3),
                }
                if case.get("reason3_sub") in sub_map3:
                    draw_maru(d, *sub_map3[case["reason3_sub"]], r=11)
    return base

# ===== セッション状態 =====
if "hl_cases"  not in st.session_state: st.session_state.hl_cases  = []
if "hl_header" not in st.session_state:
    st.session_state.hl_header = {"date": date.today(), "shift": "日勤", "leader": "前川"}

# ===== ヘッダー =====
st.subheader("📋 基本情報")
c1,c2,c3 = st.columns(3)
with c1: input_date = st.date_input("日付", value=st.session_state.hl_header["date"])
with c2: shift = st.radio("勤務帯", ["日勤","夜勤"], horizontal=True,
                           index=0 if st.session_state.hl_header["shift"]=="日勤" else 1)
with c3: leader = st.selectbox("リーダー医師名", LEADERS,
                                index=LEADERS.index(st.session_state.hl_header["leader"]))
st.session_state.hl_header = {"date": input_date, "shift": shift, "leader": leader}

# ===== 登録済み一覧 =====
st.divider()
n = len(st.session_state.hl_cases)
st.subheader(f"🚑 登録済み症例: {n}件 / 6件")
for i, c in enumerate(st.session_state.hl_cases):
    ca, cb = st.columns([6,1])
    with ca:
        st.write(f"**症例{i+1}**　{c.get('time','--:--')}　{c.get('team','') or '隊名なし'}救急隊　→ {c.get('outcome','')}")
    with cb:
        if st.button("削除", key=f"del_{i}"):
            st.session_state.hl_cases.pop(i); st.rerun()

# ===== 新規入力 =====
if n < 6:
    st.divider()
    st.subheader(f"➕ 症例 {n+1} を入力")
    cc1,cc2 = st.columns(2)
    with cc1: sel_time = st.selectbox("時刻", TIME_OPTIONS, key="inp_time")
    with cc2: team = st.selectbox("依頼先救急隊", RESCUE_TEAMS, key="inp_team")
    cc3,cc4,cc5 = st.columns(3)
    with cc3: req_count = st.selectbox("依頼回数", ["初回","2回目","3回目","4回目以上"], key="inp_req")
    with cc4: age = st.number_input("年齢（才）", min_value=0, max_value=120, value=0, step=1, key="inp_age")
    with cc5: gender = st.radio("性別", ["M","F","未記載"], horizontal=True, key="inp_gender")
    summary = st.text_area("概略", height=70, key="inp_summary", placeholder="主訴・経過を入力")
    outcome = st.radio("転帰", ["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"],
                       horizontal=True, key="inp_outcome")
    reason=reason1_sub=reason2_sub=reason3_dept=reason3_sub=""
    if outcome == "お断り":
        reason = st.radio("お断り理由",
            ["1_満床","2_マンパワー","3_院内専門科"],
            format_func=lambda x: {"1_満床":"1. 病床の都合","2_マンパワー":"2. マンパワーの問題","3_院内専門科":"3. 院内専門科の都合"}[x],
            key="inp_reason")
        if reason == "1_満床":
            reason1_sub = st.selectbox("病床理由詳細",
                ["","満床","満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"], key="inp_r1")
        elif reason == "2_マンパワー":
            reason2_sub = st.selectbox("マンパワー理由詳細",
                ["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"], key="inp_r2")
        elif reason == "3_院内専門科":
            reason3_dept = st.text_input("専門科名", key="inp_dept", placeholder="循環器")
            reason3_sub = st.selectbox("専門科理由詳細",
                ["","当該科手術中","学会等で不在","麻酔科対応不能"], key="inp_r3")
    if st.button("✅ この症例を登録", type="primary", use_container_width=True):
        st.session_state.hl_cases.append({
            "time": sel_time, "team": team, "req_count": req_count,
            "age": age if age > 0 else "",
            "gender": gender if gender != "未記載" else "",
            "summary": summary, "outcome": outcome, "reason": reason,
            "reason1_sub": reason1_sub, "reason2_sub": reason2_sub,
            "reason3_dept": reason3_dept, "reason3_sub": reason3_sub,
        })
        st.rerun()
else:
    st.info("6件登録済み（1枚の上限）。")

# ===== 出力 =====
st.divider()
oc1,oc2 = st.columns(2)
with oc1:
    if st.button("🖨️ 受付対応表を生成", type="primary", use_container_width=True,
                 disabled=(len(st.session_state.hl_cases)==0)):
        with st.spinner("生成中..."):
            result = render_hotline(st.session_state.hl_header, st.session_state.hl_cases)
        st.image(result, use_container_width=True)
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=95)
        st.download_button("📥 保存", buf.getvalue(),
            f"hotline_{input_date.strftime('%Y%m%d')}_{shift}.jpg", "image/jpeg")
with oc2:
    if st.button("🗑️ 全症例をリセット", use_container_width=True):
        st.session_state.hl_cases = []; st.rerun()
