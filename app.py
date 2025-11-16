import os
import json
import uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib
import matplotlib.pyplot as plt

# =============================================
# 🔐 페이지 설정 + 폴더 준비
# =============================================
st.set_page_config(page_title="PetMate", page_icon="🐾", layout="wide")

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
water_cols = ["log_id", "pet_id", "date", "amount_ml", "memo"]
weight_cols = ["log_id", "pet_id", "date", "weight"]

# =============================================
# 유틸 함수
# =============================================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def pet_selector(label, key=None):
    """반려동물 선택 드롭다운."""
    if "pets" not in st.session_state or len(st.session_state.pets) == 0:
        st.warning("반려동물이 등록되지 않았습니다.")
        return None
    pets = st.session_state.pets
    names = {f"{p['name']} ({p['species']})": p for p in pets}
    choice = st.selectbox(label, list(names.keys()), key=key)
    return names[choice]

def recommended_food(species, weight):
    """일일 권장 사료량(g) 단순 모델."""
    if species == "개":
        grams = weight * 30
    elif species == "고양이":
        grams = weight * 25
    else:
        grams = weight * 20
    calories = grams * 3.5
    return grams, calories

# =============================================
# 쿠키 기반 자동 로그인
# =============================================
users = load_json(USER_FILE, [])

if "user" not in st.session_state:
    st.session_state.user = None

cookie_user = st.experimental_get_cookie("petmate_user")
if cookie_user and st.session_state.user is None:
    st.session_state.user = cookie_user
    st.rerun()

# =============================================
# 세션 초기화 데이터
# =============================================
if "pets" not in st.session_state:
    st.session_state.pets = load_json(PET_FILE, [])

if "unsafe_db" not in st.session_state:
    st.session_state.unsafe_db = load_json(UNSAFE_FILE, [
        {"category":"음식","name":"초콜릿","risk":"고위험","why":"테오브로민 독성"},
        {"category":"음식","name":"포도","risk":"고위험","why":"급성 신부전 위험"}
    ])

if "hospital_events" not in st.session_state:
    st.session_state.hospital_events = load_json(HOSP_FILE, [])

if "med_schedule" not in st.session_state:
    st.session_state.med_schedule = load_json(MED_FILE, [])

feed_df = load_df(FEED_FILE, feed_cols)
water_df = load_df(WATER_FILE, water_cols)
weight_df = load_df(WEIGHT_FILE, weight_cols)

# =============================================
# 탭 생성
# =============================================
tab_login, tab_join, tab_dash, tab_profile, tab_feed, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
    "로그인", "회원가입", "대시보드", "프로필", "사료/급수", "복약", "병원 일정", "위험 검색", "데이터 관리"
])

# =============================================
# Step 2 — 로그인 화면
# =============================================
st.title("🐾 PetMate")

if st.session_state.user is None:

    with tab_login:
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")

        if st.button("로그인"):
            hashed = hash_pw(password)
            valid = any(u["username"] == username and u["password"] == hashed for u in users)
            if valid:
                st.session_state.user = username
                st.experimental_set_cookie("petmate_user", username,
                                           expires=datetime.now() + timedelta(days=30),
                                           secure=True, same_site="Lax")
                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    with tab_join:
        new_user = st.text_input("새 아이디")
        new_pass = st.text_input("새 비밀번호", type="password")

        if st.button("회원가입"):
            if not new_user or not new_pass:
                st.error("둘 다 입력하세요.")
            elif any(u["username"] == new_user for u in users):
                st.error("이미 존재하는 아이디입니다.")
            else:
                users.append({"username": new_user, "password": hash_pw(new_pass)})
                save_json(USER_FILE, users)
                st.success("회원가입 완료!")

    st.stop()

# =============================================
# Step 3 — 대시보드
# =============================================
with tab_dash:

    pet = pet_selector("차트용 반려동물 선택", key="dash_charts")

    if not pet:
        st.stop()

    st.markdown("## 📈 최근 기록 차트")

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
    # ③ 월별 병원 방문 수
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

    # ========================================================
    # ④ 도넛 차트 — 오늘 섭취량
    # ========================================================
    st.subheader("🥣 오늘 사료 섭취 도넛 차트")

    eaten = feed_chart.iloc[-1] if len(feed_chart) else 0
    grams, _ = recommended_food(pet["species"], float(pet.get("weight_kg", 0)))
    remain = max(grams - eaten, 0)

    fig, ax = plt.subplots()
    ax.pie([eaten, remain], labels=[f"{eaten} g", f"{remain} g 남음"],
           autopct="%1.1f%%", startangle=90, wedgeprops={'width':0.4})
    st.pyplot(fig)

    # ========================================================
    # ⑤ 캘린더형 병원 일정표
    # ========================================================
    st.subheader("🗓️ 병원 방문 캘린더")

    if not hosp_pet.empty:
        cal_df = hosp_pet.copy()
        cal_df["날짜"] = pd.to_datetime(cal_df["dt"]).dt.date
        cal_df = cal_df[["날짜", "title", "place"]].sort_values("날짜")
        st.dataframe(cal_df)
    else:
        st.info("병원 일정이 없습니다.")

    # ========================================================
    # ⑥ 체중 기록
    # ========================================================
    st.subheader("⚖️ 체중 기록 및 변화 그래프")

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
            st.success("저장되었습니다.")
            st.rerun()

    w_pet = weight_df[weight_df["pet_id"] == pet["id"]]
    if not w_pet.empty:
        w_chart = w_pet.set_index("date")["weight"]
        st.line_chart(w_chart)
    else:
        st.info("체중 기록이 없습니다.")

# =============================================
# Step 4 — 반려동물 프로필
# =============================================
with tab_profile:
    st.header("🐶 반려동물 프로필")

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
                        key=f"species_{p['id']}")
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

# =============================================
# Step 4 — 사료/급수 기록
# =============================================
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

# =============================================
# Step 4 — 복약 스케줄
# =============================================
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

            ok = st.form_submit_button("추가")

            if ok:
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
                        st.warning("삭제 완료!")
                        st.rerun()

# =============================================
# Step 4 — 병원 일정
# =============================================
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
                    st.session_state.hospital_events = events  # ★ 중요

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

# =============================================
# Step 5 — 위험 정보 검색
# =============================================
with tab_risk:
    st.header("⚠️ 위험 음식/식물/물품 검색")

    db = pd.DataFrame(st.session_state.unsafe_db)
    if db.empty:
        db = pd.DataFrame(columns=["category", "name", "risk", "why"])

    query = st.text_input("검색어 입력", placeholder="초콜릿, 양파, 백합꽃...")

    if query:
        view = db[db["name"].str.contains(query, case=False, na=False)]
    else:
        view = db

    st.subheader("📄 위험 리스트")
    st.dataframe(view.sort_values(["category", "risk"]))

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

# =============================================
# Step 5 — 데이터 관리
# =============================================
with tab_data:
    st.header("🗂️ 데이터 관리 / 백업")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🍽️ 사료/급수 로그 초기화"):
            save_df(FEED_FILE, pd.DataFrame(columns=feed_cols))
            save_df(WATER_FILE, pd.DataFrame(columns=water_cols))
            st.success("사료/급수 로그 초기화 완료!")

    with col2:
        if st.button("📄 프로필/스케줄/병원 DB 초기화"):
            save_json(PET_FILE, [])
            save_json(MED_FILE, [])
            save_json(HOSP_FILE, [])
            save_json(UNSAFE_FILE, [])
            st.success("모든 DB 초기화 완료!")
            st.rerun()

    st.divider()

    if st.button("👥 모든 계정 삭제"):
        save_json(USER_FILE, [])
        st.session_state.user = None
        st.experimental_delete_cookie("petmate_user")
        st.success("모든 계정 삭제 완료!")
        st.rerun()

# =============================================
# 푸터
# =============================================
st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 예제입니다. 실제 의료 상담은 수의사와 진행하세요.")
