import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib
import matplotlib.pyplot as plt

# =============================================
# 🔐 Step 0: 쿠키 기반 자동 로그인 (가장 먼저 실행)
# =============================================
st.set_page_config(page_title="PetMate", page_icon="🐾", layout="wide")

# 0-1) users.json 불러오기 (필수)
users = load_json(USER_FILE, [])

# 세션에 user가 없으면 초기화
if "user" not in st.session_state:
    st.session_state.user = None

# 0-2) 쿠키 불러오기
cookie_user = st.experimental_get_cookie("petmate_user")

# 0-3) 쿠키가 있고 아직 로그인 안된 경우 → 자동 로그인
if cookie_user and st.session_state.user is None:
    st.session_state.user = cookie_user
    st.rerun()   # 로그인된 상태로 새로고침

    # =============================================
# Step 1 — 데이터 경로 및 유틸 함수
# =============================================

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USER_FILE = os.path.join(DATA_DIR, "users.json")
PET_FILE = os.path.join(DATA_DIR, "pets.json")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")
PHOTO_DIR = os.path.join(DATA_DIR, "pet_photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
WEIGHT_FILE = os.path.join(DATA_DIR, "weight_log.csv")

feed_cols = ["log_id", "pet_id", "date", "amount_g", "memo"]
water_cols = ["log_id","pet_id","date","amount_ml","memo"]
weight_cols = ["log_id","pet_id","date","weight"]

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def load_df(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_df(path, df):
    df.to_csv(path, index=False)

def today():
    return datetime.now(tz.gettz("Asia/Seoul")).date()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# 세션 초기화
if "pets" not in st.session_state:
    st.session_state.pets = load_json(PET_FILE, [])

if "unsafe_db" not in st.session_state:
    default_unsafe = [
        {"category":"음식","name":"초콜릿","risk":"고위험","why":"테오브로민 독성"},
        {"category":"음식","name":"포도","risk":"고위험","why":"급성 신부전 위험"}
    ]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE, default_unsafe)

feed_df = load_df(FEED_FILE, feed_cols)
water_df = load_df(WATER_FILE, water_cols)
weight_df = load_df(WEIGHT_FILE, weight_cols)

# =============================================
# Step 2 — 로그인 / 회원가입 화면
# =============================================

st.set_page_config(page_title="PetMate", page_icon="🐾", layout="wide")
st.title("🐾 PetMate")

# 로그인 안 된 경우
if st.session_state.user is None:

    st.info("PetMate에 오신 것을 환영합니다! 로그인하거나 새 계정을 만들어 시작하세요.")

    # ---------------- 로그인 ---------------

        if st.button("로그인"):
            hashed = hash_pw(password)
            valid = any(u["username"] == username and u["password"] == hashed for u in users)

            if valid:
                st.session_state.user = username
                
                # 쿠키 저장 (30일 유지)
                st.experimental_set_cookie(
                    "petmate_user",
                    username,
                    expires=datetime.now() + timedelta(days=30),
                    secure=True,
                    same_site="Lax"
                )

                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    # ... (회원가입 탭 처리) ...

    # ⚠️ 로그인이 안 된 상태에서는 여기까지만 실행하고 앱을 멈춥니다.
    st.stop()

    # ---------------- 회원가입 ----------------
    with tab_join:
        new_user = st.text_input("새 아이디")
        new_pass = st.text_input("새 비밀번호", type="password")

        if st.button("회원가입"):
            if not new_user or not new_pass:
                st.error("아이디와 비밀번호를 모두 입력하세요.")
            elif any(u["username"] == new_user for u in users):
                st.error("이미 존재하는 아이디입니다.")
            else:
                users.append({"username": new_user, "password": hash_pw(new_pass)})
                save_json(USER_FILE, users)
                st.success("회원가입 완료! 로그인해 주세요.")

    st.stop()  # 로그인 전에는 아래 코드 실행 안됨

# ==============================================
# Step 3 — 대시보드 차트 섹션 (기능 유지 + 완전 정리)
# ==============================================

with tab_dash:

    pet = pet_selector("차트용 반려동물 선택", key="dash_charts")

    if not pet:
        st.stop()

    st.markdown("## 📈 최근 기록 차트")

    # 기본 날짜
    today_str = today().isoformat()
    last7 = [(today() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    # ========================================================
    # ① 최근 7일 사료 섭취량
    # ========================================================
    feed_chart = (
        feed_df[(feed_df["pet_id"] == pet["id"]) &
                (feed_df["date"].isin(last7))]
        .groupby("date")["amount_g"]
        .sum()
        .reindex(last7, fill_value=0)
    )

    st.subheader("🍽️ 최근 7일 사료 섭취량")
    st.line_chart(feed_chart)

    # ========================================================
    # ② 최근 7일 물 섭취량
    # ========================================================
    water_chart = (
        water_df[(water_df["pet_id"] == pet["id"]) &
                 (water_df["date"].isin(last7))]
        .groupby("date")["amount_ml"]
        .sum()
        .reindex(last7, fill_value=0)
    )

    st.subheader("💧 최근 7일 물 섭취량")
    st.bar_chart(water_chart)

    # ========================================================
    # ③ 병원 일정 — 월별 방문 횟수
    # ========================================================
    hosp = pd.DataFrame(st.session_state.hospital_events)
    hosp_pet = hosp[hosp["pet_id"] == pet["id"]]

    st.subheader("🏥 월별 병원 방문 수")

    if not hosp_pet.empty:
        hosp_pet["month"] = pd.to_datetime(hosp_pet["dt"]).dt.to_period("M")
        hosp_month = hosp_pet.groupby("month").size()
        st.line_chart(hosp_month)
    else:
        st.info("병원 방문 기록이 없습니다.")


    # ==============================================
    # ✔ 선택형 차트 (보고 싶은 것만 체크)
    # ==============================================
    st.markdown("## 🎛️ 선택형 차트 보기")

    show_feed = st.checkbox("🍽️ 최근 7일 사료 섭취량(중복)", value=False)
    show_water = st.checkbox("💧 최근 7일 물 섭취량(중복)", value=False)
    show_hosp = st.checkbox("🏥 월별 병원 방문 수(중복)", value=False)
    show_meds = st.checkbox("💊 오늘 복약 타임라인", value=False)

    if show_feed:
        st.subheader("🍽️ 최근 7일 사료 섭취량")
        st.line_chart(feed_chart)

    if show_water:
        st.subheader("💧 최근 7일 물 섭취량")
        st.bar_chart(water_chart)

    if show_hosp:
        st.subheader("🏥 월별 병원 방문 수")
        if not hosp_pet.empty:
            st.line_chart(hosp_month)
        else:
            st.info("병원 방문 기록 없음")

    if show_meds:
        st.subheader("💊 오늘 복약 타임라인")

        meds_pet = [m for m in st.session_state.med_schedule if m["pet_id"] == pet["id"]]
        if meds_pet:
            med_today = []
            for m in meds_pet:
                for t in m.get("times", []):
                    med_today.append({"약": m["drug"], "시간": t})

            med_today_df = pd.DataFrame(med_today).sort_values("시간")
            st.table(med_today_df)
        else:
            st.info("오늘 복약 스케줄이 없습니다.")


    # ==============================================
    # ✔ 고급 차트 섹션
    # ==============================================
    st.markdown("## 🧩 고급 데이터 분석 기능")

    # 선택 기간
    period = st.selectbox("조회 기간 선택", ["7일", "14일", "30일"], index=0)
    n = int(period.replace("일", ""))
    date_range = [(today() - timedelta(days=i)).isoformat() for i in range(n-1, -1, -1)]

    # ==================================================
    # ① 오늘 섭취량 도넛 차트
    # ==================================================
    st.subheader("🥣 오늘 사료 섭취 도넛 차트")

    eaten = feed_chart.iloc[-1] if len(feed_chart) else 0
    grams, _ = recommended_food(pet["species"], float(pet.get("weight_kg", 0)))
    remain = max(grams - eaten, 0)

    fig, ax = plt.subplots()
    ax.pie([eaten, remain], labels=[f"{eaten} g", f"{remain} g 남음"],
           autopct="%1.1f%%", startangle=90, wedgeprops={'width':0.4})
    st.pyplot(fig)


    # ==================================================
    # ② 병원 일정 캘린더형 표
    # ==================================================
    st.subheader("🗓️ 병원 방문 캘린더")

    if not hosp_pet.empty:
        cal_df = hosp_pet.copy()
        cal_df["날짜"] = pd.to_datetime(cal_df["dt"]).dt.date
        cal_df = cal_df[["날짜", "title", "place"]].sort_values("날짜")
        st.dataframe(cal_df)
    else:
        st.info("병원 일정이 없습니다.")


    # ==================================================
    # ③ 체중 기록 + 변화 그래프
    # ==================================================
    st.subheader("⚖️ 체중 기록 및 변화 그래프")

    # 체중 추가
    with st.form("weight_add"):
        new_weight = st.number_input("오늘 체중 (kg)", min_value=0.0, step=0.1)
        ok_w = st.form_submit_button("저장")
        if ok_w:
            record = pd.DataFrame({
                "log_id": [str(uuid.uuid4())],
                "pet_id": [pet["id"]],
                "date": [today_str],
                "weight": [new_weight]
            })
            weight_df_local = pd.concat([weight_df, record], ignore_index=True)
            save_df(WEIGHT_FILE, weight_df_local)
            st.success("체중이 저장되었습니다.")
            st.rerun()

    w_pet = weight_df[weight_df["pet_id"] == pet["id"]]
    if not w_pet.empty:
        w_chart = w_pet.set_index("date")["weight"]
        st.line_chart(w_chart)
    else:
        st.info("체중 기록이 없습니다.")


    # ==================================================
    # ④ 여러 마리 비교 그래프
    # ==================================================
    st.subheader("🐾 여러 반려동물 비교 그래프")

    pets = st.session_state.pets
    if len(pets) >= 2:
        selected = st.multiselect("비교할 반려동물 선택",
                                  [f"{p['name']} ({p['id']})" for p in pets])

        if selected:
            compare_data = {}
            for s in selected:
                pid = s.split("(")[-1].replace(")", "")
                name = s.split("(")[0].strip()

                series = (
                    feed_df[(feed_df["pet_id"] == pid) &
                            (feed_df["date"].isin(date_range))]
                    .groupby("date")["amount_g"]
                    .sum()
                    .reindex(date_range, fill_value=0)
                )

                compare_data[name] = series.values

            comp_df = pd.DataFrame(compare_data, index=date_range)
            st.line_chart(comp_df)

        else:
            st.info("비교할 반려동물을 선택하세요.")
    else:
        st.info("두 마리 이상 등록해야 비교 가능합니다.")
# ==============================================
# Step 4 — 반려동물 프로필
# ==============================================

with tab_profile:
    st.header("🐶 반려동물 프로필")

    # 등록 폼
    st.subheader("➕ 새 반려동물 등록")
    with st.form("pet_add_form", clear_on_submit=True):
        name = st.text_input("이름 *")
        species = st.selectbox("종 *", ["개", "고양이", "기타"])
        breed = st.text_input("품종")
        birth = st.date_input("생일", value=None)
        weight = st.number_input("체중(kg)", step=0.1, min_value=0.0)
        notes = st.text_area("메모")
        photo = st.file_uploader("사진 업로드", type=["jpg", "png", "jpeg"])
        submitted = st.form_submit_button("등록")

        if submitted:
            if not name.strip():
                st.error("이름은 필수입니다!")
            else:
                photo_path = ""
                if photo:
                    fname = f"{uuid.uuid4()}_{photo.name}"
                    photo_path = os.path.join(PHOTO_DIR, fname)
                    with open(photo_path, "wb") as f:
                        f.write(photo.read())

                new_pet = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "species": species,
                    "breed": breed,
                    "birth": birth.isoformat() if birth else "",
                    "weight_kg": float(weight),
                    "notes": notes,
                    "photo_path": photo_path
                }

                st.session_state.pets.append(new_pet)
                save_json(PET_FILE, st.session_state.pets)
                st.success(f"{name} 등록 완료!")

    st.subheader("📄 등록된 반려동물 목록")

    if not st.session_state.pets:
        st.info("등록된 반려동물이 없습니다.")
    else:
        for p in st.session_state.pets:
            with st.expander(f"{p['name']} ({p['species']})"):

                colA, colB = st.columns([2, 1])

                with colA:
                    p["name"] = st.text_input("이름", p["name"], key=f"name_{p['id']}")
                    p["species"] = st.selectbox("종", ["개", "고양이", "기타"],
                        index=["개","고양이","기타"].index(p["species"]),
                        key=f"species_{p['id']}"
                    )
                    p["breed"] = st.text_input("품종", p.get("breed",""), key=f"breed_{p['id']}")
                    p["birth"] = st.text_input("생일 (YYYY-MM-DD)", p.get("birth",""), key=f"birth_{p['id']}")
                    p["weight_kg"] = st.number_input("체중(kg)", value=float(p.get("weight_kg",0.0)), step=0.1, key=f"weight_{p['id']}")
                    p["notes"] = st.text_area("메모", p.get("notes",""), key=f"notes_{p['id']}")

                    new_photo = st.file_uploader("사진 변경", type=["jpg","png","jpeg"], key=f"photo_{p['id']}")
                    if new_photo:
                        fname = f"{uuid.uuid4()}_{new_photo.name}"
                        photo_path = os.path.join(PHOTO_DIR, fname)
                        with open(photo_path, "wb") as f:
                            f.write(new_photo.read())
                        p["photo_path"] = photo_path

                with colB:
                    if st.button("💾 저장", key=f"save_{p['id']}"):
                        save_json(PET_FILE, st.session_state.pets)
                        st.success("저장 완료!")

                    if st.button("🗑 삭제", key=f"del_{p['id']}"):
                        st.session_state.pets = [x for x in st.session_state.pets if x["id"] != p["id"]]
                        save_json(PET_FILE, st.session_state.pets)
                        st.warning(f"{p['name']} 삭제됨.")
                        st.rerun()

# ==============================================
# Step 4 — 사료/급수 기록
# ==============================================

with tab_feed:
    st.header("🍽️ 사료/급수 기록")

    pet = pet_selector("기록할 반려동물 선택", key="feed_pet")

    if pet:
        with st.form("feed_water_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                food_g = st.number_input("사료/간식 섭취량 (g)", min_value=0, step=5)
                food_memo = st.text_input("사료 메모")

            with col2:
                water_ml = st.number_input("급수량 (ml)", min_value=0, step=10)
                water_memo = st.text_input("물 메모")

            submit = st.form_submit_button("기록 저장")

            if submit:
                today_str = today().isoformat()

                if food_g > 0:
                    new_food = pd.DataFrame({
                        "log_id": [str(uuid.uuid4())],
                        "pet_id": [pet["id"]],
                        "date": [today_str],
                        "amount_g": [int(food_g)],
                        "memo": [food_memo]
                    })
                    feed_df = pd.concat([feed_df, new_food], ignore_index=True)
                    save_df(FEED_FILE, feed_df)

                if water_ml > 0:
                    new_water = pd.DataFrame({
                        "log_id": [str(uuid.uuid4())],
                        "pet_id": [pet["id"]],
                        "date": [today_str],
                        "amount_ml": [int(water_ml)],
                        "memo": [water_memo]
                    })
                    water_df = pd.concat([water_df, new_water], ignore_index=True)
                    save_df(WATER_FILE, water_df)

                st.success("기록이 저장되었습니다!")

# ==============================================
# Step 4 — 복약 스케줄
# ==============================================

with tab_med:
    st.header("💊 복약 스케줄")

    pet = pet_selector("약 복용할 반려동물 선택", key="med_pet")

    if pet:
        st.subheader("➕ 새 스케줄 추가")

        with st.form("med_form", clear_on_submit=True):
            drug = st.text_input("약 이름 *")
            dose = st.text_input("용량 (예: 5)")
            unit = st.text_input("단위 (mg, 정 등)")
            times_str = st.text_input("복용 시간들 (예: 08:00, 20:00)")

            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("시작일", today())
            with col2:
                end = st.date_input("종료일 (선택)", value=None)

            notes = st.text_area("메모")

            submit = st.form_submit_button("추가")

            if submit:
                if not drug or not times_str.strip():
                    st.error("약 이름과 시간은 필수입니다.")
                else:
                    rec = {
                        "id": str(uuid.uuid4()),
                        "pet_id": pet["id"],
                        "drug": drug,
                        "dose": dose,
                        "unit": unit,
                        "times": [t.strip() for t in times_str.split(",") if t.strip()],
                        "start": start.isoformat(),
                        "end": end.isoformat() if end else "",
                        "notes": notes,
                    }

                    med_list = load_json(MED_FILE, [])
                    med_list.append(rec)
                    save_json(MED_FILE, med_list)
                    st.success("스케줄이 추가되었습니다!")

        # 목록/삭제
        st.subheader("📄 등록된 스케줄")

        med_list = load_json(MED_FILE, [])
        meds = [m for m in med_list if m["pet_id"] == pet["id"]]

        if not meds:
            st.info("등록된 스케줄이 없습니다.")
        else:
            for m in meds:
                with st.expander(f"{m['drug']} | {', '.join(m['times'])}"):

                    st.write(f"기간: {m['start']} ~ {m['end'] or '지속'}")
                    if m.get("notes"):
                        st.caption(m["notes"])

                    if st.button("삭제", key=f"med_del_{m['id']}"):
                        med_list = [x for x in med_list if x["id"] != m["id"]]
                        save_json(MED_FILE, med_list)
                        st.warning("삭제 완료")
                        st.rerun()
# ==============================================
# Step 4 — 병원 일정
# ==============================================

with tab_hosp:
    st.header("🏥 병원 일정")

    pet = pet_selector("병원 일정 등록할 반려동물", key="hosp_pet")

    if pet:
        st.subheader("➕ 새 일정 등록")

        with st.form("hosp_form", clear_on_submit=True):
            title = st.text_input("제목 *")

            col1, col2 = st.columns(2)
            with col1:
                d = st.date_input("날짜", today())
            with col2:
                t = st.time_input("시간", time(10, 0))

            place = st.text_input("장소")
            notes = st.text_area("메모")

            submit = st.form_submit_button("추가")

            if submit:
                if not title.strip():
                    st.error("제목은 필수입니다.")
                else:
                    rec = {
                        "id": str(uuid.uuid4()),
                        "pet_id": pet["id"],
                        "title": title,
                        "dt": datetime.combine(d, t).isoformat(),
                        "place": place,
                        "notes": notes
                    }

                    events = load_json(HOSP_FILE, [])
                    events.append(rec)
                    save_json(HOSP_FILE, events)

                    st.success("일정이 등록되었습니다!")

        st.subheader("📅 등록된 병원 일정")

        events = load_json(HOSP_FILE, [])
        upcoming = sorted(
            [e for e in events if e["pet_id"] == pet["id"]],
            key=lambda x: x["dt"]
        )

        if not upcoming:
            st.info("등록된 일정이 없습니다.")
        else:
            for e in upcoming:
                dt_show = datetime.fromisoformat(e["dt"]).strftime("%Y-%m-%d %H:%M")
                st.write(f"**{dt_show}** — {e['title']} @ {e.get('place','')}")

                if e.get("notes"):
                    st.caption(e["notes"])

                if st.button("삭제", key=f"hosp_del_{e['id']}"):
                    events = [x for x in events if x["id"] != e["id"]]
                    save_json(HOSP_FILE, events)
                    st.warning("삭제되었습니다.")
                    st.rerun()

# ==============================================
# Step 5 — 위험 정보 검색 탭
# ==============================================

with tab_risk:
    st.header("⚠️ 위험 음식/식물/물품 검색")

    # DataFrame 준비
    db = pd.DataFrame(st.session_state.unsafe_db)
    if db.empty:
        db = pd.DataFrame(columns=["category", "name", "risk", "why"])

    # 검색창
    query = st.text_input("검색어 입력", placeholder="초콜릿, 양파, 백합꽃...")

    if query:
        view = db[db["name"].str.contains(query, case=False, na=False)]
    else:
        view = db

    st.subheader("📄 위험 리스트")
    st.dataframe(view.sort_values(["category", "risk"]))

    # 항목 추가
    st.subheader("➕ 새 항목 추가")

    with st.form("unsafe_add", clear_on_submit=True):
        cat = st.selectbox("분류", ["음식", "식물", "물품"])
        nm = st.text_input("이름 *")
        rk = st.selectbox("위험도", ["주의", "중간-고위험", "고위험"])
        why = st.text_area("설명")

        ok = st.form_submit_button("추가")
        if ok:
            if not nm.strip():
                st.error("이름은 필수입니다.")
            else:
                st.session_state.unsafe_db.append({
                    "category": cat,
                    "name": nm.strip(),
                    "risk": rk,
                    "why": why.strip()
                })
                save_json(UNSAFE_FILE, st.session_state.unsafe_db)
                st.success(f"{nm} 추가 완료!")

# ==============================================
# Step 5 — 데이터 관리/백업 탭
# ==============================================

with tab_data:
    st.header("🗂️ 데이터 관리 / 백업")

    col1, col2 = st.columns(2)

    # ---------------------
    # 사료/급수 초기화
    # ---------------------
    with col1:
        if st.button("🍽️ 사료/급수 로그 초기화"):
            save_df(FEED_FILE, pd.DataFrame(columns=feed_cols))
            save_df(WATER_FILE, pd.DataFrame(columns=water_cols))
            st.success("사료/급수 로그가 모두 초기화되었습니다.")

    # ---------------------
    # 프로필/스케줄/병원 초기화
    # ---------------------
    with col2:
        if st.button("📄 프로필/스케줄/병원 DB 초기화"):
            save_json(PET_FILE, [])
            save_json(MED_FILE, [])
            save_json(HOSP_FILE, [])
            save_json(UNSAFE_FILE, [])
            st.success("프로필/스케줄/병원/위험DB 초기화 완료!")
            st.rerun()

    st.divider()

    # ---------------------
    # 전체 계정 삭제
    # ---------------------
    if st.button("👥 모든 계정 삭제"):
        save_json(USER_FILE, [])
        st.session_state.user = None
        st.experimental_delete_cookie("petmate_user")
        st.success("모든 계정이 삭제되었습니다.")
        st.rerun()

# ==============================================
# Step 5 — 푸터
# ==============================================

st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 샘플입니다. 실제 의료 조언은 수의사와 상담하세요.")

