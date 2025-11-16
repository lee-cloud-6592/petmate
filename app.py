# ==============================
# PetMate: 반려동물 통합 케어 앱
# 전체 코드 (1/3)
# ==============================

import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib

# ===== 기본 경로 설정 =====
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USER_FILE = os.path.join(DATA_DIR, "users.json")
PET_FILE = os.path.join(DATA_DIR, "pets.json")
PHOTO_DIR = os.path.join(DATA_DIR, "pet_photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")

# ========== 공통 유틸 ==========

def load_json(path, default):
    """JSON 파일 로드"""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    """JSON 파일 저장"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_csv(path, cols):
    """CSV 로드 (없으면 컬럼만 있는 DataFrame)"""
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_csv(path, df):
    """CSV 저장"""
    df.to_csv(path, index=False)

def local_today():
    """한국 시각 날짜"""
    return datetime.now(tz.gettz("Asia/Seoul")).date()

def hash_password(password: str) -> str:
    """SHA-256 비밀번호 해시"""
    return hashlib.sha256(password.encode()).hexdigest()

# ========== 세션 초기화 ==========

if "user" not in st.session_state:
    st.session_state.user = None  # 로그인 사용자

if "pets" not in st.session_state:
    st.session_state.pets = load_json(PET_FILE, [])

if "med_schedule" not in st.session_state:
    st.session_state.med_schedule = load_json(MED_FILE, [])

if "hospital_events" not in st.session_state:
    st.session_state.hospital_events = load_json(HOSP_FILE, [])

if "unsafe_db" not in st.session_state:
    default_unsafe = [
        {"category": "음식", "name": "초콜릿", "risk": "고위험", "why": "카카오의 테오브로민 독성"},
        {"category": "음식", "name": "포도/건포도", "risk": "고위험", "why": "급성 신장손상 가능"}
    ]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE, default_unsafe)

# CSV 기본 구조
feed_cols = ["log_id", "pet_id", "date", "amount_g", "memo"]
water_cols = ["log_id", "pet_id", "date", "amount_ml", "memo"]

feed_df = load_csv(FEED_FILE, feed_cols)
water_df = load_csv(WATER_FILE, water_cols)

# ========== 추천값 계산 유틸 ==========

def recommended_food_grams(species: str, weight_kg: float):
    if weight_kg <= 0:
        return (0, 0)
    if species.lower() in ["개", "강아지", "dog"]:
        kcal = weight_kg * 30 + 70
        grams = round(kcal / 3.5)
    else:
        kcal = weight_kg * 60
        grams = round(kcal / 3.5)
    return grams, max(0, round(grams * 0.1))

def recommended_water_ml(weight_kg: float) -> int:
    return int(round(weight_kg * 60)) if weight_kg > 0 else 0


# ========== 반려동물 선택 UI ==========
def pet_selector(label="반려동물 선택", key=None):
    pets = st.session_state.pets
    if not pets:
        st.info("먼저 반려동물을 등록해 주세요 (왼쪽 '반려동물 프로필').")
        return None

    opts = {f"{p['name']} ({p['species']})": p for p in pets}
    choice = st.selectbox(label, list(opts.keys()), key=key)
    return opts[choice]


# ==============================
# Streamlit 페이지 구조
# ==============================
st.set_page_config(page_title="PetMate", page_icon="🐾", layout="wide")
st.title("🐾 PetMate")

# ============================
# 로그인 상태 확인
# ============================

if not st.session_state.user:

    tab_login = st.tabs(["로그인/회원가입"])[0]
    with tab_login:

        st.header("🔐 로그인 & 회원가입")
        st.info("로그인 후 모든 기능을 이용할 수 있습니다.")

        users = load_json(USER_FILE, [])

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # ---------------- 로그인 ----------------
        with tab1:
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")

            if st.button("로그인"):
                hashed = hash_password(password)
                ok = any(u["username"] == username and u["password"] == hashed for u in users)

                if ok:
                    st.session_state.user = username
                    st.success(f"{username}님 로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        # ---------------- 회원가입 ----------------
        with tab2:
            new_user = st.text_input("새 아이디")
            new_pass = st.text_input("새 비밀번호", type="password")

            if st.button("회원가입"):
                if not new_user or not new_pass:
                    st.error("아이디와 비밀번호를 모두 입력하세요.")
                elif any(u["username"] == new_user for u in users):
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    users.append({
                        "username": new_user,
                        "password": hash_password(new_pass)
                    })
                    save_json(USER_FILE, users)
                    st.success("회원가입 완료! 로그인 탭에서 로그인하세요.")
                    # ==============================
# PetMate 전체 코드 (2/3)
# ==============================

else:
    # 로그인 상태
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(f"안녕하세요, **{st.session_state.user}**님! 👋")
    with col2:
        if st.button("로그아웃"):
            st.session_state.user = None
            st.rerun()

    # 전체 탭 구성
    tab_dash, tab_profile, tab_feed, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
        "대시보드", "반려동물 프로필", "사료/급수 기록",
        "복약 알림", "병원 일정", "위험 정보 검색", "데이터 관리"
    ])


    # ==============================
    # 1) 대시보드
    # ==============================
    with tab_dash:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key="dashboard_pet_selector")

        if pet:
            col1, col2, col3 = st.columns(3)

            # 기본 정보
            with col1:
                st.subheader("기본 정보")
                st.write(f"**이름**: {pet['name']}")
                st.write(f"**종**: {pet['species']}")
                st.write(f"**체중**: {pet.get('weight_kg', '-')} kg")

                if pet.get("birth"):
                    st.write(f"**생일**: {pet['birth']}")
                if pet.get("notes"):
                    st.caption(pet["notes"])
                if pet.get("photo_path") and os.path.exists(pet["photo_path"]):
                    st.image(pet["photo_path"], width=150)

            # 사료
            with col2:
                grams, snack_limit = recommended_food_grams(
                    pet["species"],
                    float(pet.get("weight_kg", 0)) or 0
                )
                today = local_today().isoformat()

                eaten = feed_df[
                    (feed_df["pet_id"] == pet["id"]) &
                    (feed_df["date"] == today)
                ]["amount_g"].sum()

                st.subheader("사료/간식 권장량")
                st.write(f"권장: {grams} g/일  ·  간식 상한: {snack_limit} g")
                st.progress(
                    min(1.0, eaten / grams if grams else 0),
                    text=f"오늘 섭취: {int(eaten)} g"
                )

            # 물
            with col3:
                wml = recommended_water_ml(float(pet.get("weight_kg", 0)) or 0)
                drank = water_df[
                    (water_df["pet_id"] == pet["id"]) &
                    (water_df["date"] == today)
                ]["amount_ml"].sum()

                st.subheader("물 권장량")
                st.write(f"권장: {wml} ml/일")
                st.progress(
                    min(1.0, drank / wml if wml else 0),
                    text=f"오늘 급수: {int(drank)} ml"
                )


    # ==============================
    # 2) 반려동물 프로필
    # ==============================
    with tab_profile:
        st.header("🐶 반려동물 프로필")

        # -------- 등록하기 --------
        st.subheader("등록하기")
        with st.form("pet_form", clear_on_submit=True):
            name = st.text_input("이름*")
            species = st.selectbox("종*", ["개", "고양이", "기타"])
            breed = st.text_input("품종(선택)")
            birth = st.date_input("생일(선택)", value=None)
            weight = st.number_input("체중(kg)", min_value=0.0, step=0.1)
            notes = st.text_area("메모")
            photo = st.file_uploader("프로필 사진", type=["jpg","png","jpeg"])

            submitted = st.form_submit_button("추가")
            if submitted:
                photo_path = ""
                if photo:
                    filename = f"{uuid.uuid4()}_{photo.name}"
                    photo_path = os.path.join(PHOTO_DIR, filename)
                    with open(photo_path, "wb") as f:
                        f.write(photo.read())

                if not name.strip():
                    st.error("이름은 필수입니다.")
                else:
                    new_pet = {
                        "id": str(uuid.uuid4()),
                        "name": name.strip(),
                        "species": species,
                        "breed": breed.strip(),
                        "birth": birth.isoformat() if birth else "",
                        "weight_kg": float(weight),
                        "notes": notes.strip(),
                        "photo_path": photo_path
                    }

                    st.session_state.pets.append(new_pet)
                    save_json(PET_FILE, st.session_state.pets)
                    st.success(f"{name} 등록 완료!")

        # -------- 목록/편집 --------
        st.subheader("목록/편집")

        if not st.session_state.pets:
            st.info("등록된 반려동물이 없습니다.")
        else:
            for p in st.session_state.pets:
                with st.expander(f"{p['name']} ({p['species']})"):

                    colA, colB = st.columns([2,1])
                    with colA:
                        p["name"] = st.text_input("이름", p["name"], key=f"name_{p['id']}")
                        p["species"] = st.selectbox(
                            "종", ["개", "고양이", "기타"],
                            index=["개","고양이","기타"].index(p["species"]) 
                                if p["species"] in ["개","고양이","기타"] else 2,
                            key=f"species_{p['id']}"
                        )
                        p["breed"] = st.text_input("품종", p.get("breed",""), key=f"breed_{p['id']}")
                        p["birth"] = st.text_input("생일(YYYY-MM-DD)", p.get("birth",""), key=f"birth_{p['id']}")
                        p["weight_kg"] = st.number_input(
                            "체중(kg)", value=float(p.get("weight_kg",0)),
                            step=0.1, key=f"weight_{p['id']}"
                        )
                        p["notes"] = st.text_area("메모", p.get("notes",""), key=f"notes_{p['id']}")

                        new_photo = st.file_uploader(
                            "사진 변경", 
                            type=["jpg","png","jpeg"], 
                            key=f"photo_{p['id']}"
                        )

                        if new_photo:
                            filename = f"{uuid.uuid4()}_{new_photo.name}"
                            new_path = os.path.join(PHOTO_DIR, filename)
                            with open(new_path, "wb") as f:
                                f.write(new_photo.read())
                            p["photo_path"] = new_path

                    with colB:
                        if st.button("저장", key=f"save_{p['id']}"):
                            save_json(PET_FILE, st.session_state.pets)
                            st.success("저장 완료!")

                        if st.button("삭제", key=f"del_{p['id']}"):
                            st.session_state.pets = [x for x in st.session_state.pets if x["id"] != p["id"]]
                            save_json(PET_FILE, st.session_state.pets)
                            st.warning("삭제했습니다.")


    # ==============================
    # 3) 사료/급수 기록
    # ==============================
    with tab_feed:
        st.header("🍽️ 사료/급수 기록")

        pet = pet_selector(key="feed_pet_selector")

        if pet:
            with st.form("feed_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    food_g = st.number_input("사료/간식 섭취량 (g)", min_value=0, step=5)
                    food_memo = st.text_input("메모(선택)")

                with col2:
                    water_ml = st.number_input("급수량 (ml)", min_value=0, step=10)
                    water_memo = st.text_input("물 관련 메모(선택)")

                submitted = st.form_submit_button("💾 저장")

                if submitted:
                    today = local_today().isoformat()

                    # 사료 기록
                    if food_g > 0:
                        new_food = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [pet["id"]],
                            "date": [today],
                            "amount_g": [int(food_g)],
                            "memo": [food_memo.strip()]
                        })
                        feed_df.loc[len(feed_df)] = new_food.iloc[0]

                    # 물 기록
                    if water_ml > 0:
                        new_water = pd.DataFrame({
                            "log_id": [str(uuid.uuid.uuid4())],
                            "pet_id": [pet["id"]],
                            "date": [today],
                            "amount_ml": [int(water_ml)],
                            "memo": [water_memo.strip()]
                        })
                        water_df.loc[len(water_df)] = new_water.iloc[0]

                    save_csv(FEED_FILE, feed_df)
                    save_csv(WATER_FILE, water_df)

                    st.success("기록이 저장되었습니다.")


    # ==============================
    # 4) 복약 스케줄
    # ==============================
    with tab_med:
        st.header("💊 복약 스케줄")

        pet = pet_selector(key="med_pet_selector")
        if pet:

            st.subheader("스케줄 추가")
            with st.form("med_form", clear_on_submit=True):
                drug = st.text_input("약 이름*")
                dose = st.text_input("용량 예: 5")
                unit = st.text_input("단위 예: mg")

                times_str = st.text_input("복용 시간(HH:MM, 여러 개 → 쉼표)", placeholder="08:00, 20:00")

                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input("시작일", value=local_today())
                with col2:
                    end = st.date_input("종료일(선택)", value=None)

                notes = st.text_area("메모")

                ok = st.form_submit_button("추가")

                if ok:
                    times = [t.strip() for t in times_str.split(",") if t.strip()]
                    if not drug or not times:
                        st.error("약 이름과 복용 시간은 필수입니다.")
                    else:
                        rec = {
                            "id": str(uuid.uuid4()),
                            "pet_id": pet["id"],
                            "drug": drug.strip(),
                            "dose": dose.strip(),
                            "unit": unit.strip(),
                            "times": times,
                            "start": start.isoformat(),
                            "end": end.isoformat() if end else "",
                            "notes": notes.strip()
                        }

                        st.session_state.med_schedule.append(rec)
                        save_json(MED_FILE, st.session_state.med_schedule)
                        st.success("추가 완료!")

            st.subheader("등록된 스케줄")
            meds = [m for m in st.session_state.med_schedule if m["pet_id"] == pet["id"]]

            if not meds:
                st.info("등록된 스케줄이 없습니다.")
            else:
                for m in meds:
                    with st.expander(f"{m['drug']} {m['dose']}{m['unit']} | {', '.join(m['times'])}"):
                        st.write(f"기간: {m['start']} ~ {m['end'] or '지속'}")
                        if m.get("notes"):
                            st.caption(m["notes"])

                        if st.button("삭제", key=f"del_med_{m['id']}"):
                            st.session_state.med_schedule = [
                                x for x in st.session_state.med_schedule if x["id"] != m["id"]
                            ]
                            save_json(MED_FILE, st.session_state.med_schedule)
                            st.warning("삭제했습니다.")


    # ==============================
    # 5) 병원 일정
    # ==============================
    with tab_hosp:
        st.header("🏥 병원 일정")

        pet = pet_selector(key="hosp_pet_selector")

        if pet:

            st.subheader("새 일정 추가")
            with st.form("hosp_form", clear_on_submit=True):
                title = st.text_input("제목*")

                col1, col2 = st.columns(2)
                with col1:
                    d = st.date_input("날짜", value=local_today())
                with col2:
                    t = st.time_input("시간", value=time(hour=10))

                place = st.text_input("장소")
                notes = st.text_area("메모")

                ok = st.form_submit_button("추가")

                if ok:
                    if not title.strip():
                        st.error("제목은 필수입니다.")
                    else:
                        dt_iso = datetime.combine(d, t).isoformat()

                        rec = {
                            "id": str(uuid.uuid4()),
                            "pet_id": pet["id"],
                            "title": title.strip(),
                            "dt": dt_iso,
                            "place": place.strip(),
                            "notes": notes.strip()
                        }

                        st.session_state.hospital_events.append(rec)
                        save_json(HOSP_FILE, st.session_state.hospital_events)

                        st.success("추가 완료!")

            st.subheader("다가오는 일정")
            upcoming = sorted(
                [e for e in st.session_state.hospital_events if e["pet_id"] == pet["id"]],
                key=lambda x: x["dt"]
            )

            if not upcoming:
                st.info("등록된 일정이 없습니다.")
            else:
                for e in upcoming:
                    dt_kst = datetime.fromisoformat(e["dt"]).astimezone(
                        tz.gettz("Asia/Seoul")
                    ).strftime("%Y-%m-%d %H:%M")

                    st.write(f"**{dt_kst}** · {e['title']} ({e.get('place','')})")
                    if e.get("notes"):
                        st.caption(e["notes"])

                    if st.button("삭제", key=f"del_evt_{e['id']}"):
                        st.session_state.hospital_events = [
                            x for x in st.session_state.hospital_events if x["id"] != e["id"]
                        ]
                        save_json(HOSP_FILE, st.session_state.hospital_events)
                        st.warning("삭제했습니다.")
                        # ==============================
# PetMate 전체 코드 (3/3)
# ==============================

    # ==============================
    # 6) 위험 정보 검색
    # ==============================
    with tab_risk:
        st.header("⚠️ 위험 음식/식물/물품 검색")

        q = st.text_input("검색어를 입력하세요", placeholder="예: 초콜릿, 양파")

        db = pd.DataFrame(st.session_state.unsafe_db)

        # 일부 유저 DB에 없는 컬럼 대비 처리
        for col in ["category", "risk", "why"]:
            if col not in db.columns:
                db[col] = ""

        # 검색 실행
        view = db[db["name"].str.contains(q, case=False, na=False)] if q else db
        st.dataframe(view.sort_values(["category", "risk"]))

        # --- DB 추가/수정 ---
        with st.expander("🔧 항목 추가"):
            with st.form("unsafe_add", clear_on_submit=True):
                cat = st.selectbox("분류", ["음식", "식물", "물품"])
                nm = st.text_input("이름")
                rk = st.selectbox("위험도", ["주의", "중간-고위험", "고위험"])
                why = st.text_area("설명")

                ok = st.form_submit_button("추가")
                if ok:
                    st.session_state.unsafe_db.append({
                        "category": cat,
                        "name": nm.strip(),
                        "risk": rk,
                        "why": why.strip()
                    })
                    save_json(UNSAFE_FILE, st.session_state.unsafe_db)
                    st.success("추가되었습니다.")


    # ==============================
    # 7) 데이터 관리
    # ==============================
    with tab_data:
        st.header("🗂️ 데이터 관리 / 초기화")

        col1, col2 = st.columns(2)

        # 로그 초기화
        with col1:
            if st.button("사료/급수 로그 초기화"):
                save_csv(FEED_FILE, pd.DataFrame(columns=feed_cols))
                save_csv(WATER_FILE, pd.DataFrame(columns=water_cols))
                st.success("사료/급수 로그가 초기화되었습니다!")

        # 프로필/스케줄 초기화
        with col2:
            if st.button("프로필/복약/일정/위험DB 초기화"):
                save_json(PET_FILE, [])
                save_json(MED_FILE, [])
                save_json(HOSP_FILE, [])
                save_json(UNSAFE_FILE, [])
                st.session_state.pets = []
                st.session_state.med_schedule = []
                st.session_state.hospital_events = []
                st.session_state.unsafe_db = []
                st.success("모든 데이터가 초기화되었습니다!")

        st.divider()

        # 계정 삭제
        if st.button("👥 모든 회원 계정 삭제 (주의!)"):
            save_json(USER_FILE, [])
            st.session_state.user = None
            st.success("모든 계정이 삭제되었습니다.")
            st.rerun()


# ==============================
# 푸터
# ==============================
st.divider()
st.caption("© 2025 PetMate • 포트폴리오용 샘플. 실제 진료는 수의사와 상담하세요.")
