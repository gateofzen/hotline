import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os
from datetime import date

st.set_page_config(page_title="ホットライン受付対応表", layout="centered")
st.title("📞 ホットライン受付対応表")

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
    "/usr/local/share/fonts/NotoSansCJK-Regular.ttc",
]

# フォント診断
_FONT_PATH = None
for _p in FONT_CANDIDATES:
    if os.path.exists(_p):
        _FONT_PATH = _p
        break
if _FONT_PATH is None:
    st.error("⚠️ 日本語フォントが見つかりません。packages.txt に fonts-noto-cjk を追加してください。")
else:
    st.caption(f"✅ フォント: {_FONT_PATH}")

def get_font(size):
    global _FONT_PATH
    if _FONT_PATH is None:
        for path in FONT_CANDIDATES:
            if os.path.exists(path):
                _FONT_PATH = path
                break
    if _FONT_PATH:
        return ImageFont.truetype(_FONT_PATH, max(10, size))
    return ImageFont.load_default()

RESCUE_TEAMS = [
    "","中央","大通","桑園","山鼻","北","篠路","新光","東","栄","東苗穂",
    "白石","菊水","厚別","厚別西","豊平","西岡","平岸","清田","南","定山渓",
    "西","前田","西野","手稲","石山","あいの里","北野","警防","豊水","幌西",
    "藤野","八軒","北郷","札苗","苗穂","北エルム","東モエレ",
]
LEADERS   = ["前川","中嶋","森木","小舘","遠藤"]
WEEKDAYS  = ["月","火","水","木","金","土","日"]
# 各ブロック上端Y（1413×2000基準）
BLOCK_TOPS_REF = [168, 460, 749, 1039, 1329, 1619]
TIME_OPTIONS = [""] + [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0,60,5)]

def render_hotline(header, cases):
    base = Image.open("hotline.png").convert("RGB")
    W, H = base.size
    # 設計基準サイズからのスケール係数
    sx = W / 1413
    sy = H / 2000
    s  = min(sx, sy)   # フォントは小さい方に合わせる

    def X(v): return int(v * sx)
    def Y(v): return int(v * sy)
    def R(v): return max(4, int(v * s))
    def F(v): return get_font(max(8, int(v * s)))

    def dm(cx, cy, r=14):
        d.ellipse([X(cx)-R(r), Y(cy)-R(r), X(cx)+R(r), Y(cy)+R(r)], outline="black", width=max(2, R(4)))

    d = ImageDraw.Draw(base)

    # フォント（縮小済み）
    f34 = F(34); f30 = F(30); f26 = F(26); f22 = F(22); f28 = F(28)

    # ===== ヘッダー（基準Y=108-168）=====
    dt = header["date"]
    wd = WEEKDAYS[dt.weekday()]

    # 年月日曜日
    d.text((X(260), Y(112)), str(dt.year),  font=f30, fill="black")
    d.text((X(420), Y(112)), str(dt.month), font=f30, fill="black")
    d.text((X(485), Y(112)), str(dt.day),   font=f30, fill="black")
    d.text((X(590), Y(112)), wd,            font=f30, fill="black")

    # 日勤(X=701) / 夜勤(X=778)
    if header["shift"] == "日勤":
        dm(701, 138, r=22)
    else:
        dm(778, 138, r=22)

    # リーダー医師名
    d.text((X(1080), Y(106)), header["leader"], font=f34, fill="black")

    # ===== 症例ブロック =====
    for i, case in enumerate(cases):
        if i >= 6: break
        yt  = BLOCK_TOPS_REF[i]
        yn  = yt - 5     # 時刻/救急隊名行
        yc  = yt + 21    # 症例行
        yg  = yt + 60    # 概略
        yn2 = yt + 131   # 転帰行
        # お断り理由Y（スキャン確定: rel=222,247,276）
        yr1 = yt + 222; yr2 = yt + 247; yr3 = yt + 276

        # 時刻
        if case.get("time"):
            d.text((X(304), Y(yn)), case["time"], font=f26, fill="black")

        # 依頼回数
        if case.get("req_count") == "初回":
            dm(620, yn+14, r=16)
        else:
            num = (case.get("req_count") or "").replace("回目","").replace("回","")
            if num:
                d.text((X(718), Y(yn)), num, font=f26, fill="black")

        # 依頼先
        if case.get("team"):
            d.text((X(970), Y(yn)), case["team"], font=f26, fill="black")

        # 年齢
        if case.get("age"):
            d.text((X(235), Y(yc)), str(case["age"]), font=f26, fill="black")

        # 性別（スキャン確定: M=475, F=512）
        if case.get("gender") == "M":
            dm(460, yc+20, r=14)
        elif case.get("gender") == "F":
            dm(512, yc+20, r=14)

        # 概略
        lines = []
        line = ""
        for ch in (case.get("summary") or ""):
            line += ch
            if len(line) >= 30: lines.append(line); line = ""
        if line: lines.append(line)
        for li, ln in enumerate(lines[:2]):
            d.text((X(168), Y(yg + li*32)), ln, font=f22, fill="black")

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
            dm(*tenki_map[outcome], r=16)

        # お断り理由
        if outcome == "お断り":
            reason = case.get("reason","")
            if reason == "1_満床":
                dm(160, yr1, r=12)   # "1." はX=160
                sub_map = {
                    "満床": (263,yr1), "満床に準ずる状態": (405,yr1),
                    "ICU個室(感染等)満床": (600,yr1), "熱傷患者受入不能": (815,yr1),
                }
                if case.get("reason1_sub") in sub_map:
                    dm(*sub_map[case["reason1_sub"]], r=12)
            elif reason == "2_マンパワー":
                dm(295, yr2, r=12)   # "2." X=295
                sub_map2 = {
                    "他患の処置・手術等で余力なし": (448,yr2),
                    "別の救急患者の搬入直前・直後": (645,yr2),
                }
                if case.get("reason2_sub") in sub_map2:
                    dm(*sub_map2[case["reason2_sub"]], r=12)
            elif reason == "3_院内専門科":
                dm(295, yr3, r=12)   # "3." X=295
                if case.get("reason3_dept"):
                    d.text((X(415), Y(yr3-20)), case["reason3_dept"].rstrip("科"), font=f22, fill="black")
                sub_map3 = {
                    "当該科手術中": (595,yr3), "学会等で不在": (745,yr3),
                    "麻酔科対応不能": (890,yr3),
                }
                if case.get("reason3_sub") in sub_map3:
                    dm(*sub_map3[case["reason3_sub"]], r=12)
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
