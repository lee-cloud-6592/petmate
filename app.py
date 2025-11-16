# PetMate: 반려동물 통합 케어 앱 (Streamlit) - 완전판
import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib

# ===== 경로 설정 =====
DATA_DIR = "data"
USER_FILE = os.path.join(DATA_DIR, "users.json")
PHOTO_DIR = os.path.join(DATA_DIR, "pet_photos")
PET_FILE = os.path.join(DATA_DIR, "pets.json")
FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
WEIGHT_FILE = os.path.join(DATA_DIR, "weight_log.csv")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")
COOKIE_FILE = os.path.join(DATA_DIR, "login_cookie.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===== 유틸 함수 =====
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

def load_csv(path, cols):
    if os.path.exists(path):
        try: 
            df = pd.read_csv(path)
            if df.empty:
                return pd.DataFrame(columns=cols)
            return df
        except: 
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_csv(path, df): 
    df.to_csv(path, index=False)

def local_today(): 
    return datetime.now(tz.gettz("Asia/Seoul")).date()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    return load_json(USER_FILE, [])

def save_users(users):
    save_json(USER_FILE, users)

# ===== 쿠키 관련 함수 =====
def save_login_cookie(username):
    cookie_data = {
        "username": username,
        "timestamp": datetime.now().isoformat()
    }
    save_json(COOKIE_FILE, cookie_data)

def load_login_cookie():
    cookie = load_json(COOKIE_FILE, None)
    if cookie and "username" in cookie:
        try:
            saved_time = datetime.fromisoformat(cookie["timestamp"])
            if datetime.now() - saved_time < timedelta(days=7):
                return cookie["username"]
        except:
            pass
    return None

def clear_login_cookie():
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)

# ===== 로그인 상태 초기화 =====
if "user" not in st.session_state:
    saved_user = load_login_cookie()
    if saved_user:
        users = load_users()
        if any(u["username"] == saved_user for u in users):
            st.session_state.user = saved_user
        else:
            clear_login_cookie()
            st.session_state.user = None
    else:
        st.session_state.user = None

# ===== 데이터 로드 =====
if "pets" not in st.session_state: 
    st.session_state.pets = load_json(PET_FILE, [])
if "med_schedule" not in st.session_state: 
    st.session_state.med_schedule = load_json(MED_FILE, [])
if "hospital_events" not in st.session_state: 
    st.session_state.hospital_events = load_json(HOSP_FILE, [])
if "unsafe_db" not in st.session_state:
    default_unsafe = [
        {"category":"음식","name":"초콜릿","risk":"고위험","why":"카카오의 메틸잔틴(테오브로민) 독성"},
        {"category":"음식","name":"포도/건포도","risk":"고위험","why":"급성 신장손상 보고"}
    ]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE, default_unsafe)

# CSV 컬럼 정의
feed_cols = ["log_id", "pet_id", "date", "amount_g", "memo"]
water_cols = ["log_id", "pet_id", "date", "amount_ml", "memo"]
weight_cols = ["log_id", "pet_id", "date", "weight_kg", "memo"]

# ===== 권장량 계산 함수 =====
def recommended_food_grams(species: str, weight_kg: float) -> tuple:
    if weight_kg <= 0: 
        return (0, 0)
    if species.lower() in ["개", "강아지", "dog"]:
        kcal = weight_kg * 30 + 70
        grams = round(kcal / 3.5)
    else:
        kcal = 60 * weight_kg
        grams = round(kcal / 3.5)
    return grams, max(0, round(grams * 0.1))

def recommended_water_ml(weight_kg: float) -> int:
    return int(round(weight_kg * 60)) if weight_kg > 0 else 0

def pet_selector(label="반려동물 선택", key=None):
    pets = st.session_state.pets
    if not pets:
        st.info("먼저 반려동물을 등록해 주세요.")
        return None
    opts = {f"{p['name']} ({p['species']})": p for p in pets}
    return opts[st.selectbox(label, list(opts.keys()), key=key)]

# ===== 페이지 설정 =====
st.set_page_config(page_title="PetMate", page_icon="🐾", layout="wide")
st.title("🐾 PetMate")

# ===== 로그인/회원가입 =====
if not st.session_state.user:
    st.info("🔐 PetMate에 오신 것을 환영합니다!")
    
    users = load_users()
    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        st.subheader("로그인")
        username = st.text_input("아이디", key="login_user")
        password = st.text_input("비밀번호", type="password", key="login_pass")
        remember = st.checkbox("로그인 상태 유지 (7일)", value=True)
        
        if st.button("로그인", type="primary"):
            hashed = hash_password(password)
            if any(u["username"] == username and u["password"] == hashed for u in users):
                st.session_state.user = username
                if remember:
                    save_login_cookie(username)
                st.success(f"✅ {username}님 로그인 성공!")
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")

    with tab2:
        st.subheader("회원가입")
        new_user = st.text_input("새 아이디", key="signup_user")
        new_pass = st.text_input("새 비밀번호", type="password", key="signup_pass")
        new_pass_confirm = st.text_input("비밀번호 확인", type="password", key="signup_pass_confirm")
        
        if st.button("회원가입", type="primary"):
            if not new_user or not new_pass:
                st.error("❌ 아이디와 비밀번호를 모두 입력해주세요.")
            elif new_pass != new_pass_confirm:
                st.error("❌ 비밀번호가 일치하지 않습니다.")
            elif any(u["username"] == new_user for u in users):
                st.error("❌ 이미 존재하는 아이디입니다.")
            else:
                users.append({"username": new_user, "password": hash_password(new_pass)})
                save_users(users)
                st.success("✅ 회원가입 완료! 로그인하세요.")

else:
    # ===== 로그인 상태 - 헤더 =====
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(f"안녕하세요, **{st.session_state.user}**님! 👋")
    with col2:
        if st.button("로그아웃"):
            st.session_state.user = None
            clear_login_cookie()
            st.rerun()

    # ===== 메인 탭 =====
    tabs = st.tabs(["📊 대시보드", "🐶 프로필", "🍽️ 사료/급수", "📈 건강", "💊 복약", "🏥 병원", "⚠️ 위험정보", "🗂️ 데이터"])
    
    # ===== 대시보드 =====
    with tabs[0]:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key="dash_pet")
        
        if pet:
            feed_df = load_csv(FEED_FILE, feed_cols)
            water_df = load_csv(WATER_FILE, water_cols)
            weight_df = load_csv(WEIGHT_FILE, weight_cols)
            
            col1, col2, col3 = st.columns(3)
            
            # 기본 정보
            with col1:
                st.subheader("기본 정보")
                st.write(f"**이름**: {pet['name']}")
                st.write(f"**종**: {pet['species']}")
                st.write(f"**체중**: {pet.get('weight_kg', '-')} kg")
                if pet.get("birth"): 
                    st.write(f"**생일**: {pet['birth']}")
                if pet.get("photo_path") and os.path.exists(pet["photo_path"]):
                    st.image(pet["photo_path"], width=150)
            
            # 사료 섭취량
            with col2:
                grams, snack = recommended_food_grams(pet["species"], float(pet.get("weight_kg", 0) or 0))
                today = local_today().isoformat()
                eaten = feed_df[(feed_df["pet_id"]==pet["id"]) & (feed_df["date"]==today)]["amount_g"].sum()
                st.subheader("사료/간식")
                st.write(f"권장: {grams} g/일")
                st.write(f"간식 상한: {snack} g")
                st.progress(min(1.0, eaten/grams if grams else 0), text=f"오늘: {int(eaten)} g")
            
            # 급수량
            with col3:
                water_ml = recommended_water_ml(float(pet.get("weight_kg", 0) or 0))
                drank = water_df[(water_df["pet_id"]==pet["id"]) & (water_df["date"]==today)]["amount_ml"].sum()
                st.subheader("물")
                st.write(f"권장: {water_ml} ml/일")
                st.progress(min(1.0, drank/water_ml if water_ml else 0), text=f"오늘: {int(drank)} ml")
            
            # 최근 7일 차트
            st.divider()
            st.subheader("📊 최근 7일")
            
            end_date = local_today()
            last7 = [(end_date - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**🍽️ 사료 섭취량**")
                feed_chart = feed_df[(feed_df["pet_id"]==pet["id"]) & (feed_df["date"].isin(last7))]\
                    .groupby("date")["amount_g"].sum().reindex(last7, fill_value=0)
                st.line_chart(feed_chart)
            
            with col_b:
                st.write("**💧 급수량**")
                water_chart = water_df[(water_df["pet_id"]==pet["id"]) & (water_df["date"].isin(last7))]\
                    .groupby("date")["amount_ml"].sum().reindex(last7, fill_value=0)
                st.bar_chart(water_chart)

    # ===== 프로필 =====
    with tabs[1]:
        st.header("🐶 반려동물 프로필")
        
        with st.form("pet_form", clear_on_submit=True):
            st.subheader("새 반려동물 등록")
            name = st.text_input("이름*")
            species = st.selectbox("종*", ["개", "고양이", "기타"])
            breed = st.text_input("품종")
            birth = st.date_input("생일", value=None)
            weight = st.number_input("체중(kg)", min_value=0.0, step=0.1)
            notes = st.text_area("메모")
            photo = st.file_uploader("프로필 사진", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("추가"):
                if not name.strip():
                    st.error("❌ 이름은 필수입니다.")
                else:
                    photo_path = ""
                    if photo:
                        photo_path = os.path.join(PHOTO_DIR, f"{uuid.uuid4()}_{photo.name}")
                        with open(photo_path, "wb") as f: 
                            f.write(photo.read())
                    
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
                    
                    # 초기 체중 기록
                    if weight > 0:
                        weight_df = load_csv(WEIGHT_FILE, weight_cols)
                        new_w = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [new_pet["id"]],
                            "date": [local_today().isoformat()],
                            "weight_kg": [float(weight)],
                            "memo": ["초기 등록"]
                        })
                        weight_df = pd.concat([weight_df, new_w], ignore_index=True)
                        save_csv(WEIGHT_FILE, weight_df)
                    
                    st.success(f"✅ {name} 등록 완료!")
                    st.rerun()
        
        st.divider()
        st.subheader("등록된 반려동물")
        
        if not st.session_state.pets:
            st.info("등록된 반려동물이 없습니다.")
        else:
            for p in st.session_state.pets:
                with st.expander(f"{p['name']} ({p['species']})"):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        p["name"] = st.text_input("이름", value=p["name"], key=f"n_{p['id']}")
                        p["species"] = st.selectbox("종", ["개", "고양이", "기타"],
                            index=["개", "고양이", "기타"].index(p["species"]) if p["species"] in ["개", "고양이", "기타"] else 2,
                            key=f"s_{p['id']}")
                        p["weight_kg"] = st.number_input("체중(kg)", value=float(p.get("weight_kg", 0)), 
                            step=0.1, key=f"w_{p['id']}")
                    with col_b:
                        if st.button("💾 저장", key=f"save_{p['id']}"):
                            save_json(PET_FILE, st.session_state.pets)
                            st.success("✅ 저장")
                            st.rerun()
                        if st.button("🗑️ 삭제", key=f"del_{p['id']}"):
                            st.session_state.pets = [x for x in st.session_state.pets if x["id"]!=p["id"]]
                            save_json(PET_FILE, st.session_state.pets)
                            st.warning("⚠️ 삭제")
                            st.rerun()

    # ===== 사료/급수 =====
    with tabs[2]:
        st.header("🍽️ 사료/급수 기록")
        pet = pet_selector(key="feed_pet")
        
        if pet:
            with st.form("feed_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    food = st.number_input("사료/간식 (g)", min_value=0, step=5)
                    food_memo = st.text_input("메모")
                with c2:
                    water = st.number_input("물 (ml)", min_value=0, step=10)
                    water_memo = st.text_input("메모", key="water_memo")
                
                if st.form_submit_button("💾 저장"):
                    feed_df = load_csv(FEED_FILE, feed_cols)
                    water_df = load_csv(WATER_FILE, water_cols)
                    today = local_today().isoformat()
                    
                    if food > 0:
                        new_f = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [pet["id"]],
                            "date": [today],
                            "amount_g": [int(food)],
                            "memo": [food_memo.strip()]
                        })
                        feed_df = pd.concat([feed_df, new_f], ignore_index=True)
                        save_csv(FEED_FILE, feed_df)
                    
                    if water > 0:
                        new_w = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [pet["id"]],
                            "date": [today],
                            "amount_ml": [int(water)],
                            "memo": [water_memo.strip()]
                        })
                        water_df = pd.concat([water_df, new_w], ignore_index=True)
                        save_csv(WATER_FILE, water_df)
                    
                    st.success("✅ 저장 완료!")
                    st.rerun()

    # ===== 건강 데이터 =====
    with tabs[3]:
        st.header("📈 건강 데이터")
        pet = pet_selector(key="health_pet")
        
        if pet:
            weight_df = load_csv(WEIGHT_FILE, weight_cols)
            
            # 체중 기록
            with st.form("weight_form", clear_on_submit=True):
                st.subheader("체중 기록")
                col1, col2 = st.columns(2)
                with col1:
                    w_date = st.date_input("날짜", value=local_today())
                    new_w = st.number_input("체중 (kg)", min_value=0.0, step=0.1, 
                                           value=float(pet.get("weight_kg", 0)))
                with col2:
                    w_memo = st.text_area("메모")
                
                if st.form_submit_button("💾 기록"):
                    if new_w > 0:
                        rec = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [pet["id"]],
                            "date": [w_date.isoformat()],
                            "weight_kg": [float(new_w)],
                            "memo": [w_memo.strip()]
                        })
                        weight_df = pd.concat([weight_df, rec], ignore_index=True)
                        save_csv(WEIGHT_FILE, weight_df)
                        
                        # 프로필 업데이트
                        for p in st.session_state.pets:
                            if p["id"] == pet["id"]:
                                p["weight_kg"] = float(new_w)
                        save_json(PET_FILE, st.session_state.pets)
                        
                        st.success("✅ 기록 완료!")
                        st.rerun()
            
            st.divider()
            
            # 차트
            period = st.selectbox("기간", ["최근 7일", "최근 30일", "전체"], index=1)
            
            end_date = local_today()
            if period == "최근 7일":
                start_date = end_date - timedelta(days=6)
            elif period == "최근 30일":
                start_date = end_date - timedelta(days=29)
            else:
                start_date = None
            
            # 체중 차트
            st.subheader("⚖️ 체중 변화")
            pet_w = weight_df[weight_df["pet_id"] == pet["id"]].copy()
            
            if not pet_w.empty:
                pet_w["date"] = pd.to_datetime(pet_w["date"])
                pet_w = pet_w.sort_values("date")
                if start_date:
                    pet_w = pet_w[pet_w["date"] >= pd.Timestamp(start_date)]
                
                if not pet_w.empty:
                    w_chart = pet_w.set_index("date")["weight_kg"]
                    st.line_chart(w_chart)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("현재", f"{pet_w.iloc[-1]['weight_kg']:.1f} kg")
                    with col2:
                        if len(pet_w) > 1:
                            change = pet_w.iloc[-1]['weight_kg'] - pet_w.iloc[0]['weight_kg']
                            st.metric("변화", f"{change:+.1f} kg")
                    with col3:
                        st.metric("평균", f"{pet_w['weight_kg'].mean():.1f} kg")
                else:
                    st.info("선택한 기간에 기록이 없습니다.")
            else:
                st.info("체중 기록이 없습니다.")
            
            st.divider()
            
            # 사료 차트
            st.subheader("🍽️ 사료 섭취량")
            feed_df = load_csv(FEED_FILE, feed_cols)
            pet_f = feed_df[feed_df["pet_id"] == pet["id"]].copy()
            
            if not pet_f.empty:
                pet_f["date"] = pd.to_datetime(pet_f["date"])
                if start_date:
                    pet_f = pet_f[pet_f["date"] >= pd.Timestamp(start_date)]
                
                if not pet_f.empty:
                    daily_f = pet_f.groupby("date")["amount_g"].sum()
                    st.line_chart(daily_f)
                else:
                    st.info("기간 내 기록 없음")
            else:
                st.info("사료 기록 없음")
            
            st.divider()
            
            # 급수 차트
            st.subheader("💧 급수량")
            water_df = load_csv(WATER_FILE, water_cols)
            pet_wat = water_df[water_df["pet_id"] == pet["id"]].copy()
            
            if not pet_wat.empty:
                pet_wat["date"] = pd.to_datetime(pet_wat["date"])
                if start_date:
                    pet_wat = pet_wat[pet_wat["date"] >= pd.Timestamp(start_date)]
                
                if not pet_wat.empty:
                    daily_w = pet_wat.groupby("date")["amount_ml"].sum()
                    st.bar_chart(daily_w)
                else:
                    st.info("기간 내 기록 없음")
            else:
                st.info("급수 기록 없음")

    # ===== 복약 =====
    with tabs[4]:
        st.header("💊 복약 스케줄")
        pet = pet_selector(key="med_pet")
        
        if pet:
            with st.form("med_form", clear_on_submit=True):
                st.subheader("새 스케줄")
                drug = st.text_input("약 이름*")
                dose = st.text_input("용량")
                unit = st.text_input("단위")
                times = st.text_input("시간 (HH:MM, 콤마 구분)", placeholder="08:00, 20:00")
                c1, c2 = st.columns(2)
                with c1: 
                    start = st.date_input("시작일", value=local_today())
                with c2: 
                    end = st.date_input("종료일", value=None)
                notes = st.text_area("메모")
                
                if st.form_submit_button("추가"):
                    if drug.strip() and times.strip():
                        rec = {
                            "id": str(uuid.uuid4()),
                            "pet_id": pet["id"],
                            "drug": drug.strip(),
                            "dose": dose.strip(),
                            "unit": unit.strip(),
                            "times": [t.strip() for t in times.split(",") if t.strip()],
                            "start": start.isoformat(),
                            "end": end.isoformat() if end else "",
                            "notes": notes.strip()
                        }
                        st.session_state.med_schedule.append(rec)
                        save_json(MED_FILE, st.session_state.med_schedule)
                        st.success("✅ 추가 완료!")
                        st.rerun()
                    else:
                        st.error("❌ 약 이름과 시간은 필수입니다.")
            
            st.divider()
            st.subheader("등록된 스케줄")
            meds = [m for m in st.session_state.med_schedule if m["pet_id"]==pet["id"]]
            
            if not meds:
                st.info("등록된 스케줄이 없습니다.")
            else:
                for m in meds:
                    with st.expander(f"{m['drug']} - {', '.join(m.get('times', []))}"):
                        st.write(f"**용량**: {m['dose']}{m['unit']}")
                        st.write(f"**기간**: {m.get('start')} ~ {m.get('end') or '지속'}")
                        if m.get("notes"):
                            st.caption(m["notes"])
                        if st.button("🗑️ 삭제", key=f"med_del_{m['id']}"):
                            st.session_state.med_schedule = [x for x in st.session_state.med_schedule if x["id"]!=m["id"]]
                            save_json(MED_FILE, st.session_state.med_schedule)
                            st.warning("삭제됨")
                            st.rerun()

    # ===== 병원 =====
    with tabs[5]:
        st.header("🏥 병원 일정")
        pet = pet_selector(key="hosp_pet")
        
        if pet:
            with st.form("hosp_form", clear_on_submit=True):
                st.subheader("일정 추가")
                title = st.text_input("제목*")
                c1, c2 = st.columns(2)
                with c1: 
                    d = st.date_input("날짜", value=local_today())
                with c2: 
                    t = st.time_input("시간", value=time(10, 0))
                place = st.text_input("장소")
                notes = st.text_area("메모")
                
                if st.form_submit_button("추가"):
                    if title.strip():
                        rec = {
                            "id": str(uuid.uuid4()),
                            "pet_id": pet["id"],
                            "title": title.strip(),
                            "dt": datetime.combine(d, t).isoformat(),
                            "place": place.strip(),
                            "notes": notes.strip()
                        }
                        st.session_state.hospital_events.append(rec)
                        save_json(HOSP_FILE, st.session_state.hospital_events)
                        st.success("✅ 추가 완료!")
                        st.rerun()
                    else:
                        st.error("❌ 제목은 필수입니다.")
            
            st.divider()
            st.subheader("다가오는 일정")
            events = [e for e in st.session_state.hospital_events if e["pet_id"]==pet["id"]]
            events = sorted(events, key=lambda x: x["dt"])
            
            if not events:
                st.info("등록된 일정이 없습니다.")
            else:
                for e in events:
                    dt_str = datetime.fromisoformat(e["dt"]).strftime("%Y-%m-%d %H:%M")
                    st.write(f"**{dt_str}** · {e['title']} @ {e.get('place', '')}")
                    if e.get("notes"):
                        st.caption(e["notes"])
                    if st.button("🗑️ 삭제", key=f"hosp_del_{e['id']}"):
                        st.session_state.hospital_events = [x for x in st.session_state.hospital_events if x["id"]!=e["id"]]
                        save_json(HOSP_FILE, st.session_state.hospital_events)
                        st.warning("삭제됨")
                        st.rerun()

    # ===== 위험 정보 =====
    with tabs[6]:
        st.header("⚠️ 위험 음식/식물/물품")
        
        query = st.text_input("검색어", placeholder="예: 초콜릿, 양파")
        
        db = pd.DataFrame(st.session_state.unsafe_db)
        for col in ["category", "risk"]:
            if col not in db.columns:
                db[col] = "기타"
        
        if query:
            view = db[db["name"].str.contains(query, case=False, na=False)]
        else:
            view = db
        
        st.dataframe(view.sort_values(["category", "risk"]), use_container_width=True)
        
        with st.expander("➕ 항목 추가"):
            with st.form("unsafe_form", clear_on_submit=True):
                cat = st.selectbox("분류", ["음식", "식물", "물품"])
                name = st.text_input("이름")
                risk = st.selectbox("위험도", ["주의", "중간-고위험", "고위험"])
                why = st.text_area("이유/설명")
                
                if st.form_submit_button("추가"):
                    if name.strip():
                        st.session_state.unsafe_db.append({
                            "category": cat,
                            "name": name.strip(),
                            "risk": risk,
                            "why": why.strip()
                        })
                        save_json(UNSAFE_FILE, st.session_state.unsafe_db)
                        st.success("✅ 추가됨!")
                        st.rerun()
                    else:
                        st.error("❌ 이름을 입력하세요.")

    # ===== 데이터 관리 =====
    with tabs[7]:
        st.header("🗂️ 데이터 관리")
        
        st.subheader("데이터 초기화")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🍽️ 사료/급수/체중 초기화", use_container_width=True):
                save_csv(FEED_FILE, pd.DataFrame(columns=feed_cols))
                save_csv(WATER_FILE, pd.DataFrame(columns=water_cols))
                save_csv(WEIGHT_FILE, pd.DataFrame(columns=weight_cols))
                st.success("✅ 초기화 완료")
                st.rerun()
        
        with col2:
            if st.button("🐾 프로필/일정 초기화", use_container_width=True):
                save_json(PET_FILE, [])
                save_json(MED_FILE, [])
                save_json(HOSP_FILE, [])
                save_json(UNSAFE_FILE, [])
                st.session_state.pets = []
                st.session_state.med_schedule = []
                st.session_state.hospital_events = []
                st.session_state.unsafe_db = []
                st.success("✅ 초기화 완료")
                st.rerun()
        
        st.divider()
        
        st.subheader("⚠️ 위험 구역")
        st.warning("아래 버튼을 누르면 모든 계정이 삭제됩니다.")
        if st.button("🗑️ 모든 계정 삭제", type="primary"):
            save_json(USER_FILE, [])
            st.session_state.user = None
            clear_login_cookie()
            st.success("✅ 모든 계정이 삭제되었습니다.")
            st.rerun()

# ===== 푸터 =====
st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 샘플. 실제 의료 조언은 수의사와 상담하세요.")
