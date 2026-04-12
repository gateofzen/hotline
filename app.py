import streamlit as st
from leader_schedule import get_leader, schedule_editor_widget
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont
import io, os, json
from datetime import date, datetime

st.set_page_config(page_title="ホットライン受付対応表", layout="centered")
st.title("📞 ホットライン受付対応表")

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]
_FONT_PATH = None
for _p in FONT_CANDIDATES:
    if os.path.exists(_p):
        _FONT_PATH = _p; break
if _FONT_PATH is None:
    st.error("⚠️ 日本語フォントが見つかりません。packages.txt に fonts-noto-cjk を追加してください。")

def get_font(size):
    if _FONT_PATH:
        return ImageFont.truetype(_FONT_PATH, max(10, size))
    return ImageFont.load_default()

# ===== ファイル永続化 =====
CASES_FILE = "hl_cases.json"

def load_cases():
    if os.path.exists(CASES_FILE):
        try:
            with open(CASES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_cases(cases):
    try:
        with open(CASES_FILE, "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
    except: pass

# ===== 時刻から勤務帯判定 =====
def time_to_shift(time_str):
    """'HH:MM' → '日勤' or '夜勤'。8:30-16:30=日勤"""
    try:
        h, m = map(int, time_str.split(":"))
        minutes = h * 60 + m
        if 8*60+30 <= minutes < 16*60+30:
            return "日勤"
        return "夜勤"
    except:
        return "夜勤"

def get_shift_date(case_date_str, time_str):
    """症例の時刻が00:00-08:30の場合は前日夜勤扱い → shift_date を返す
    case_date_str: 'YYYY-MM-DD', time_str: 'HH:MM'"""
    try:
        from datetime import date as _d, timedelta
        h, m = map(int, time_str.split(":"))
        minutes = h * 60 + m
        base = _d.fromisoformat(case_date_str)
        if minutes < 8*60+30:  # 00:00-08:30 → 前日夜勤
            return (base - timedelta(days=1)).isoformat()
        return case_date_str
    except:
        return case_date_str

RESCUE_TEAMS = [
    "","警防","中央","大通","山鼻","豊水","幌西","北","北エルム","あいの里",
    "篠路","新光","東","東モエレ","栄","札苗","苗穂","白石","南郷","菊水",
    "北郷","厚別","厚別西","豊平","月寒","平岸","西岡","清田","北野","南",
    "藤野","定山渓","西","発寒","八軒","西野","手稲","前田",
]
LEADERS   = ["前川","中嶋","森木","小舘","遠藤","提嶋"]
WEEKDAYS  = ["月","火","水","木","金","土","日"]
BLOCK_TOPS = [168, 460, 749, 1039, 1329, 1619]
TIME_OPTIONS = [""] + [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0,60,5)]

def render_hotline(header, cases, sheet_no=1):
    base = Image.open("hotline.png").convert("RGB")
    W, H = base.size
    sx=W/1413; sy=H/2000; s=min(sx,sy)
    def X(v): return int(v*sx)
    def Y(v): return int(v*sy)
    def R(v): return max(4,int(v*s))
    def F(v): return get_font(max(8,int(v*s)))
    def dm(cx,cy,r=14):
        d.ellipse([X(cx)-R(r),Y(cy)-R(r),X(cx)+R(r),Y(cy)+R(r)],outline="black",width=max(2,R(4)))

    def draw_check(cx, cy):
        """□の中にチェックマークを描画"""
        s = R(10)
        x, y = X(cx), Y(cy)
        d.line([(x-s, y), (x-s//3, y+s), (x+s, y-s)], fill="black", width=max(2,R(3)))

    d = ImageDraw.Draw(base)
    f34=F(34); f30=F(30); f26=F(26); f22=F(22)

    # ===== No.（ヘッダー行 Y=109-168, X=0-194の中央）=====
    f_no = F(42)
    no_str = str(sheet_no)
    bb = d.textbbox((0,0), no_str, font=f_no)
    tw = bb[2]-bb[0]; th = bb[3]-bb[1]
    no_x = X(104 + (194-104-tw)//2 + 8)   # 少し右
    no_y = Y(109)                            # 上端ぴったり
    d.text((no_x, no_y), no_str, font=f_no, fill="black")

    # ===== ヘッダー =====
    dt = header["date"] if isinstance(header["date"],date) else date.fromisoformat(str(header["date"]))
    wd = WEEKDAYS[dt.weekday()]
    d.text((X(260),Y(114)),str(dt.year),font=f30,fill="black")
    d.text((X(420),Y(114)),str(dt.month),font=f30,fill="black")
    d.text((X(485),Y(114)),str(dt.day),font=f30,fill="black")
    d.text((X(590),Y(114)),wd,font=f30,fill="black")
    shift = header["shift"]
    if shift=="日勤": dm(701,138,r=18)
    else: dm(778,138,r=18)
    d.text((X(1080),Y(106)),header["leader"],font=f34,fill="black")

    for i,case in enumerate(cases):
        if i>=6: break
        yt=BLOCK_TOPS[i]
        yn=yt-5; yc=yt+21; yg=yt+60; yn2=yt+131
        yr1=yt+222; yr2=yt+247; yr3=yt+276

        if case.get("time"): d.text((X(300),Y(yn)),case["time"],font=f26,fill="black")
        if case.get("req_count")=="初回": dm(620,yn+20,r=16)
        else:
            num=(case.get("req_count") or "").replace("回目","").replace("回","")
            if num: d.text((X(718),Y(yn)),num,font=f26,fill="black")
        if case.get("team"): d.text((X(970),Y(yn)),case["team"],font=f26,fill="black")
        if case.get("age"): d.text((X(235),Y(yc)),str(case["age"]),font=f26,fill="black")
        if case.get("gender")=="M": dm(432,yc+26,r=14)
        elif case.get("gender")=="F": dm(500,yc+26,r=14)

        lines=[]; line=""
        for ch in (case.get("summary") or ""):
            line+=ch
            if len(line)>=30: lines.append(line); line=""
        if line: lines.append(line)
        for li,ln in enumerate(lines[:2]):
            d.text((X(168),Y(yg+li*30)),ln,font=f22,fill="black")

        outcome=case.get("outcome","")
        tenki_map={"搬入":(172,yn2),"お断り":(270,yn2),"2次やかかりつけ医案内":(500,yn2),"患者都合":(743,yn2),"その他":(172,yt+160)}
        if outcome in tenki_map:
            cx,cy = tenki_map[outcome]
            draw_check(cx,cy)

        if outcome=="お断り":
            reason=case.get("reason","")
            if reason=="1_満床":
                dm(292,yr1,r=12)  # yr3 cluster[0]と同じX=292
                sub_map={
                    "満床・満床に準ずる状態":(503,yr1),  # 519→503（少し左）
                    "ICU個室(感染等)満床":    (730,yr1),  # cluster[19-20]間・左 X=730
                    "熱傷患者受入不能":       (948,yr1),  # cluster[27]の左 X=948
                }
                if case.get("reason1_sub") in sub_map:
                    draw_check(*sub_map[case["reason1_sub"]])
            elif reason=="2_マンパワー":
                dm(295,yr2,r=12)
                sub_map2={"他患の処置・手術等で余力なし":(465,yr2),"別の救急患者の搬入直前・直後":(735,yr2)}
                if case.get("reason2_sub") in sub_map2:
                    draw_check(*sub_map2[case["reason2_sub"]])
            elif reason=="3_院内専門科":
                dm(292,yr3,r=12)  # cluster[0] X=292
                if case.get("reason3_dept"):
                    d.text((X(415),Y(yr3-20)),case["reason3_dept"].rstrip("科"),font=f22,fill="black")
                sub_map3={
                    "当該科手術中":(673,yr3),  # cluster[11-12]間・中央 X=673
                    "学会等で不在":(820,yr3),  # cluster[19-20]間・中央右 X=820
                    "麻酔科対応不能":(960,yr3), # cluster[24-25]間・中央右 X=960
                }
                if case.get("reason3_sub") in sub_map3:
                    draw_check(*sub_map3[case["reason3_sub"]])
    return base

# ===== セッション状態 =====
if "hl_cases" not in st.session_state:
    st.session_state.hl_cases = load_cases()
if "hl_header" not in st.session_state:
    st.session_state.hl_header = {"date": date.today().isoformat(), "leader": "前川"}
if "hl_images" not in st.session_state:
    st.session_state.hl_images = []

# ===== ヘッダー =====
st.subheader("📋 基本情報")
c1,c2 = st.columns(2)
with c1:
    # 日付: セッションに保存済みならそれを使う、なければ今日
    _today = date.today()
    saved_date = st.session_state.hl_header.get("date", _today.isoformat())
    # セッションの日付が今日と異なる場合（別日にセッションが残っていた）は今日にリセット
    if saved_date != _today.isoformat() and "hl_date_set" not in st.session_state:
        saved_date = _today.isoformat()
    st.session_state.hl_date_set = True
    input_date = st.date_input("日付", value=date.fromisoformat(str(saved_date)))
with c2:
    # 入力日付とその時刻（現在時刻）からデフォルトリーダーを決定
    from datetime import timezone as _hltz, timedelta as _hltd
    _hl_jst = __import__('datetime').datetime.now(_hltz(_hltd(hours=9)))
    _hl_shift_tmp = "日勤" if 8*60+30 <= _hl_jst.hour*60+_hl_jst.minute < 16*60+30 else "夜勤"
    _hl_leader_def = get_leader(input_date, _hl_shift_tmp)
    _hl_def_idx = LEADERS.index(_hl_leader_def) if _hl_leader_def in LEADERS else LEADERS.index(st.session_state.hl_header.get("leader","前川")) if st.session_state.hl_header.get("leader") in LEADERS else 0
    leader = st.selectbox("リーダー医師名", LEADERS, index=_hl_def_idx)
st.session_state.hl_header = {"date": input_date.isoformat(), "leader": leader}

# ===== 登録済み一覧 =====
st.divider()
cases = st.session_state.hl_cases
n = len(cases)

# 日勤・夜勤で件数集計
# 入力日付とtime_to_shiftで日勤/夜勤を判定
# 00:00-08:30は夜勤だが、前日夜勤として同じ夜勤グループに含める
nisshin = [c for c in cases if time_to_shift(c.get("time","")) == "日勤"]
yashin  = [c for c in cases if time_to_shift(c.get("time","")) == "夜勤"]
# 夜勤の日付判定：00:00-08:30は前日のshift_dateになるが、
# 同じ出力シートにまとめるため表示上はそのまま夜勤として扱う
st.markdown(f"**🚑 登録済み: {n}件（日勤 {len(nisshin)}件 / 夜勤 {len(yashin)}件）**")

# 編集モード管理
if "hl_editing" not in st.session_state:
    st.session_state.hl_editing = None

if n > 0:
    st.markdown("""<style>
    [data-testid="stHorizontalBlock"] > div { min-width:0!important; }
    button[kind="secondary"] { padding:1px 6px!important; font-size:11px!important; min-height:24px!important; height:24px!important; line-height:1!important; }
    </style>""", unsafe_allow_html=True)

    for i, c in enumerate(cases):
        t = c.get("time","--:--")
        team = c.get("team","") or "不明"
        outcome = c.get("outcome","")
        ci, ce, cd = st.columns([8, 1, 1])
        with ci:
            age_str = f"{c.get('age','')}才" if c.get("age") else ""
            gender_str = c.get("gender","")
            info = " ".join(filter(None, [age_str, gender_str]))
            st.markdown(f"<div style='font-size:15px;padding:4px 0'><b>{i+1}.{t}</b> {team} {info} →{outcome}</div>",
                        unsafe_allow_html=True)
        with ce:
            if st.button("✏", key=f"hl_edit_{i}", help="編集"):
                st.session_state.hl_editing = i
                st.rerun()
        with cd:
            if st.button("🗑", key=f"hl_del_{i}", help="削除"):
                st.session_state.hl_cases.pop(i)
                save_cases(st.session_state.hl_cases)
                if st.session_state.hl_editing == i:
                    st.session_state.hl_editing = None
                st.rerun()

# ===== 編集モード =====
hl_edit_idx = st.session_state.hl_editing
if hl_edit_idx is not None and 0 <= hl_edit_idx < len(cases):
    ec = cases[hl_edit_idx]
    st.divider()
    st.subheader(f"✏️ 症例 {hl_edit_idx+1} を編集")
    ec1,ec2 = st.columns(2)
    with ec1:
        e_time = st.selectbox("時刻", TIME_OPTIONS,
            index=TIME_OPTIONS.index(ec["time"]) if ec.get("time") in TIME_OPTIONS else 0,
            key="e_time")
        if e_time: st.caption(f"→ **{time_to_shift(e_time)}**")
    with ec2:
        _team_val = ec.get("team","")
        _team_opts = RESCUE_TEAMS + ["その他（直接入力）"]
        _team_idx = RESCUE_TEAMS.index(_team_val) if _team_val in RESCUE_TEAMS else (len(RESCUE_TEAMS) if _team_val else 0)
        e_team_sel = st.selectbox("依頼先救急隊", _team_opts, index=_team_idx, key="e_team")
        if e_team_sel == "その他（直接入力）":
            e_team = st.text_input("救急隊名を入力", value=_team_val if _team_val not in RESCUE_TEAMS else "", key="e_team_other", placeholder="例: 石狩")
        else:
            e_team = e_team_sel
    ec3,ec4,ec5 = st.columns(3)
    with ec3:
        e_req = st.selectbox("依頼回数", ["初回","2回目","3回目","4回目以上"],
            index=["初回","2回目","3回目","4回目以上"].index(ec["req_count"]) if ec.get("req_count") in ["初回","2回目","3回目","4回目以上"] else 0,
            key="e_req")
    with ec4:
        e_age = st.number_input("年齢（才）", min_value=0, max_value=120,
            value=int(ec["age"]) if ec.get("age") else 0, step=1, key="e_age")
    with ec5:
        gender_opts = ["M","F","未記載"]
        e_gender = st.radio("性別", gender_opts, horizontal=True,
            index=gender_opts.index(ec["gender"]) if ec.get("gender") in gender_opts else 2,
            key="e_gender")
    e_summary = st.text_area("概略", value=ec.get("summary",""), height=70, key="e_summary")
    e_outcome = st.radio("転帰", ["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"],
        horizontal=True,
        index=["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"].index(ec["outcome"]) if ec.get("outcome") in ["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"] else 0,
        key="e_outcome")
    e_reason=e_r1=e_r2=e_r3dept=e_r3sub=""
    if e_outcome == "お断り":
        reason_opts = ["1_満床","2_マンパワー","3_院内専門科"]
        e_reason = st.radio("お断り理由", reason_opts,
            format_func=lambda x:{"1_満床":"1. 病床の都合","2_マンパワー":"2. マンパワーの問題","3_院内専門科":"3. 院内専門科の都合"}[x],
            index=reason_opts.index(ec["reason"]) if ec.get("reason") in reason_opts else 0,
            key="e_reason")
        if e_reason=="1_満床":
            e_r1 = st.selectbox("病床理由詳細",["","満床・満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"],
                index=["","満床・満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"].index(ec.get("reason1_sub","")) if ec.get("reason1_sub","") in ["","満床・満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"] else 0,
                key="e_r1")
        elif e_reason=="2_マンパワー":
            e_r2 = st.selectbox("マンパワー理由詳細",["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"],
                index=["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"].index(ec.get("reason2_sub","")) if ec.get("reason2_sub","") in ["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"] else 0,
                key="e_r2")
        elif e_reason=="3_院内専門科":
            e_r3dept = st.text_input("専門科名", value=ec.get("reason3_dept",""), key="e_r3dept")
            e_r3sub = st.selectbox("専門科理由詳細",["","当該科手術中","学会等で不在","麻酔科対応不能"],
                index=["","当該科手術中","学会等で不在","麻酔科対応不能"].index(ec.get("reason3_sub","")) if ec.get("reason3_sub","") in ["","当該科手術中","学会等で不在","麻酔科対応不能"] else 0,
                key="e_r3sub")
    ex1,ex2 = st.columns(2)
    with ex1:
        if st.button("💾 保存", type="primary", use_container_width=True, key="e_save"):
            st.session_state.hl_cases[hl_edit_idx] = {
                "time":e_time,"team":e_team,"req_count":e_req,
                "age":e_age if e_age>0 else "","gender":e_gender if e_gender!="未記載" else "",
                "summary":e_summary,"outcome":e_outcome,"reason":e_reason,
                "reason1_sub":e_r1,"reason2_sub":e_r2,
                "reason3_dept":e_r3dept,"reason3_sub":e_r3sub,
            }
            save_cases(st.session_state.hl_cases)
            st.session_state.hl_editing = None
            st.rerun()
    with ex2:
        if st.button("キャンセル", use_container_width=True, key="e_cancel"):
            st.session_state.hl_editing = None
            st.rerun()

# ===== 新規入力 =====
st.divider()
st.subheader(f"➕ 症例 {n+1} を入力")
cc1,cc2=st.columns(2)
with cc1:
    # 現在時刻（JST）を切り捨て（5分刻み）でデフォルトに
    from datetime import timezone, timedelta
    _jst = timezone(timedelta(hours=9))
    _now = datetime.now(_jst)
    _rounded = f"{_now.hour:02d}:{(_now.minute // 5) * 5:02d}"
    _nearest_idx = TIME_OPTIONS.index(_rounded) if _rounded in TIME_OPTIONS else 0
    sel_time=st.selectbox("時刻", TIME_OPTIONS, index=_nearest_idx, key="inp_time")
    if sel_time:
        st.caption(f"→ **{time_to_shift(sel_time)}**")
with cc2:
    team_sel = st.selectbox("依頼先救急隊", RESCUE_TEAMS + ["その他（直接入力）"], key="inp_team")
    if team_sel == "その他（直接入力）":
        team = st.text_input("救急隊名を入力", key="inp_team_other", placeholder="例: 石狩")
    else:
        team = team_sel
cc3,cc4,cc5=st.columns(3)
with cc3: req_count=st.selectbox("依頼回数",["初回","2回目","3回目","4回目以上"],key="inp_req")
with cc4: age=st.number_input("年齢（才）",min_value=0,max_value=120,value=0,step=1,key="inp_age")
with cc5: gender=st.radio("性別",["M","F","未記載"],horizontal=True,key="inp_gender")
summary=st.text_area("概略",height=70,key="inp_summary",placeholder="主訴・経過を入力")
outcome=st.radio("転帰",["搬入","お断り","2次やかかりつけ医案内","患者都合","その他"],horizontal=True,key="inp_outcome")
reason=reason1_sub=reason2_sub=reason3_dept=reason3_sub=""
if outcome=="お断り":
    reason=st.radio("お断り理由",["1_満床","2_マンパワー","3_院内専門科"],
        format_func=lambda x:{"1_満床":"1. 病床の都合","2_マンパワー":"2. マンパワーの問題","3_院内専門科":"3. 院内専門科の都合"}[x],
        key="inp_reason")
    if reason=="1_満床":
        reason1_sub=st.selectbox("病床理由詳細",
            ["","満床・満床に準ずる状態","ICU個室(感染等)満床","熱傷患者受入不能"],key="inp_r1")
    elif reason=="2_マンパワー":
        reason2_sub=st.selectbox("マンパワー理由詳細",
            ["","他患の処置・手術等で余力なし","別の救急患者の搬入直前・直後"],key="inp_r2")
    elif reason=="3_院内専門科":
        reason3_dept=st.text_input("専門科名",key="inp_dept",placeholder="循環器")
        reason3_sub=st.selectbox("専門科理由詳細",["","当該科手術中","学会等で不在","麻酔科対応不能"],key="inp_r3")

if st.button("✅ この症例を登録",type="primary",use_container_width=True):
    st.session_state.hl_cases.append({
        "time":sel_time,"team":team,"req_count":req_count,
        "age":age if age>0 else "","gender":gender if gender!="未記載" else "",
        "summary":summary,"outcome":outcome,"reason":reason,
        "reason1_sub":reason1_sub,"reason2_sub":reason2_sub,
        "reason3_dept":reason3_dept,"reason3_sub":reason3_sub,
    })
    save_cases(st.session_state.hl_cases)
    st.rerun()

# ===== 印刷ウィジェット =====
def hl_make_print_widget(pil_img, key="print"):
    import base64
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=95)
    b64 = base64.b64encode(buf.getvalue()).decode()
    html = f"""<!DOCTYPE html>
<html><head><style>
  body{{margin:0;padding:0;background:transparent;font-family:sans-serif}}
  @media screen{{
    .img-wrap{{display:none}}
    .btn{{display:block;width:100%;height:38px;padding:0 14px;box-sizing:border-box;
      background:transparent;color:inherit;border:1px solid rgba(49,51,63,0.2);
      border-radius:4px;font-size:0.875rem;cursor:pointer}}
    .btn:hover{{border-color:#f63366;color:#f63366}}
    @media(prefers-color-scheme:dark){{.btn{{border-color:rgba(250,250,250,0.2);color:#fff}}}}
  }}
  @media print{{
    .btn{{display:none}}
    .img-wrap{{display:block}}
    @page{{size:A4;margin:0}}
    html,body{{height:100%;overflow:hidden;margin:0;padding:0}}
    img{{width:100%;height:auto;max-height:100vh;display:block}}
  }}
</style></head><body>
<div class="img-wrap"><img src="data:image/jpeg;base64,{b64}"></div>
<button class="btn" onclick="window.print()">🖨️ 印刷</button>
</body></html>"""
    return html

# ===== 出力（日勤・夜勤を別紙）=====
st.divider()
oc1,oc2=st.columns(2)
with oc1:
    if st.button("🖨️ 受付対応表を生成",type="primary",use_container_width=True,
                 disabled=(len(st.session_state.hl_cases)==0)):
        date_str = input_date.strftime('%Y%m%d')
        all_images = []

        for shift_label, shift_cases in [("日勤", nisshin), ("夜勤", yashin)]:
            if not shift_cases:
                continue
            st.write(f"### 📄 {shift_label}（{len(shift_cases)}件）")
            n_sh = max(1,(len(shift_cases)+5)//6)
            # 夜勤で最初の症例が00:00-08:30なら前日日付で出力
            _first_time = shift_cases[0].get("time","") if shift_cases else ""
            _h = int(_first_time.split(":")[0]) if _first_time and ":" in _first_time else 12
            if shift_label == "夜勤" and _h < 8 or (shift_label == "夜勤" and _h == 8 and int(_first_time.split(":")[1]) < 30):
                from datetime import timedelta
                _header_date = (input_date - timedelta(days=1)).isoformat()
            else:
                _header_date = input_date.isoformat()
            header_for_render = {"date": _header_date, "shift": shift_label, "leader": leader}
            for sh in range(n_sh):
                sheet_cases = shift_cases[sh*6:sh*6+6]
                with st.spinner(f"{shift_label} No.{sh+1} 生成中..."):
                    result = render_hotline(header_for_render, sheet_cases, sheet_no=sh+1)
                st.write(f"**{shift_label} No.{sh+1}**（症例{sh*6+1}〜{min(sh*6+len(sheet_cases),len(shift_cases))}）")
                st.image(result, use_container_width=True)
                buf=io.BytesIO()
                result.save(buf,format="JPEG",quality=95)
                fname = f"hotline_{date_str}_{shift_label}_No{sh+1}.jpg"
                all_images.append((fname, buf.getvalue()))
                # 印刷ボタン
                import streamlit.components.v1 as _comp
                _comp.html(hl_make_print_widget(result, f"hl_print_{shift_label}_{sh}"), height=38)

        st.session_state.hl_images = all_images
        if all_images:
            st.success(f"✅ {len(all_images)}枚の受付対応表を生成しました。")

    # PDF一括保存
    if st.session_state.get("hl_images"):
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.utils import ImageReader
            from PIL import Image as PILImage

            A4_W, A4_H = A4
            MARGIN = 28
            avail_w = A4_W - 2*MARGIN
            avail_h = A4_H - 2*MARGIN

            pdf_buf = io.BytesIO()
            c = rl_canvas.Canvas(pdf_buf, pagesize=A4)
            for _, img_bytes in st.session_state.hl_images:
                img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
                iw, ih = img.size
                scale = min(avail_w/iw, avail_h/ih)
                pw, ph = iw*scale, ih*scale
                x = MARGIN + (avail_w - pw) / 2
                y = MARGIN + (avail_h - ph) / 2
                img_buf2 = io.BytesIO()
                img.save(img_buf2, format="JPEG", quality=95)
                img_buf2.seek(0)
                c.drawImage(ImageReader(img_buf2), x, y, width=pw, height=ph)
                c.showPage()
            c.save()
            pdf_buf.seek(0)
            pdf_name = f"hotline_{input_date.strftime('%Y%m%d')}.pdf"
            st.download_button(
                "📄 全受付対応表をPDFで保存（A4印刷用）",
                pdf_buf.getvalue(), pdf_name, "application/pdf",
                use_container_width=True, type="primary",
                key="hl_pdf_dl"
            )
        except Exception as e:
            st.error(f"PDF生成エラー: {e}")

with oc2:
    if st.button("🗑️ 全症例をリセット",use_container_width=True):
        st.session_state.hl_cases=[]
        st.session_state.hl_images=[]
        save_cases([])
        st.rerun()

# ===== 勤務表リーダー設定 =====
with st.expander("📅 勤務表リーダー設定", expanded=False):
    from datetime import timezone as _stz2, timedelta as _std2
    from leader_schedule import parse_schedule_pdf, save_schedule, load_schedule
    _now_hl = __import__('datetime').datetime.now(_stz2(_std2(hours=9)))
    _sh_hl = "日勤" if 8*60+30 <= _now_hl.hour*60+_now_hl.minute < 16*60+30 else "夜勤"
    _ld_hl = get_leader(input_date, _sh_hl)
    if _ld_hl:
        st.info(f"👤 {input_date.month}/{input_date.day} {_sh_hl}のリーダー: **{_ld_hl}**")
    else:
        st.warning(f"⚠️ {input_date.month}/{input_date.day} {_sh_hl}のリーダーが未設定です")
    pdf_file_hl = st.file_uploader("📄 勤務表PDFをアップロード（毎月20日頃に更新）",
                                    type=["pdf"], key="sched_pdf_hl",
                                    label_visibility="collapsed")
    if pdf_file_hl:
        with st.spinner("勤務表を解析中..."):
            result_hl, msg_hl = parse_schedule_pdf(pdf_file_hl.read())
        if result_hl:
            sched_hl = load_schedule()
            sched_hl.update(result_hl)
            save_schedule(sched_hl)
            st.success(f"✅ {msg_hl}")
        else:
            st.error(f"❌ {msg_hl}")
    st.caption("PDFアップロード後に内容を確認・修正できます")
    schedule_editor_widget("hotline_sched")
