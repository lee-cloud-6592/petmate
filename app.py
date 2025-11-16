    import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib

# ===== 쿠키 기반 로그인 유지 =====
cookie_user = st.experimental_get_cookie("petmate_user")

# 세션에 사용자 정보가 없고 쿠키는 존재하면 → 자동 로그인 처리
if ("user" not in st.session_state or st.session_state.user is None) and cookie_user:
    st.session_state.user = cookie_user
    st.rerun() # **추가: 자동 로그인 후 바로 새로고침하여 세션 상태 유지**
    
# ===== 경로 설정 =====
DATA_DIR = "data"
USER_FILE = os.path.join(DATA_DIR, "users.json")
PHOTO_DIR = os.path.join(DATA_DIR, "pet_photos")
os.makedirs(PHOTO_DIR, exist_ok=True)
PET_FILE = os.path.join(DATA_DIR, "pets.json")
FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")
# **추가: 체중 파일 경로 정의**
WEIGHT_FILE = os.path.join(DATA_DIR, "weight_log.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# ===== 유틸 =====
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f: return json.load(f)
        except: return default
    return default
def save_json(path,data):
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
if "user" not in st.session_state:
    st.session_state.user = None   # 현재 로그인한 사용자

def load_users():
    return load_json(USER_FILE, [])

def save_users(users):
    save_json(USER_FILE, users)

def load_csv(path,cols):
    if os.path.exists(path):
        try: return pd.read_csv(path)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)
def save_csv(path,df): df.to_csv(path,index=False)
def local_today(): return datetime.now(tz.gettz("Asia/Seoul")).date()

def hash_password(password: str) -> str:
    """SHA-256으로 비밀번호를 해시"""
    return hashlib.sha256(password.encode()).hexdigest()


# ===== 초기 세션 =====
if "pets" not in st.session_state: st.session_state.pets = load_json(PET_FILE,[])
if "med_schedule" not in st.session_state: st.session_state.med_schedule = load_json(MED_FILE,[])
if "hospital_events" not in st.session_state: st.session_state.hospital_events = load_json(HOSP_FILE,[])
if "unsafe_db" not in st.session_state:
    default_unsafe=[{"category":"음식","name":"초콜릿","risk":"고위험","why":"카카오의 메틸잔틴(테오브로민) 독성"},
                    {"category":"음식","name":"포도/건포도","risk":"고위험","why":"급성 신장손상 보고"}]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE,default_unsafe)

feed_cols=["log_id","pet_id","date","amount_g","memo"]
water_cols=["log_id","pet_id","date","amount_ml","memo"]
# **추가: 체중 기록 컬럼 정의**
weight_cols = ["log_id", "pet_id", "date", "weight"]

feed_df = load_csv(FEED_FILE,feed_cols)
water_df = load_csv(WATER_FILE,water_cols)
# **추가: 체중 기록 데이터프레임 로드**
weight_df = load_csv(WEIGHT_FILE, weight_cols)


def recommended_food_grams(species:str,weight_kg:float)->tuple:
    if weight_kg<=0: return (0,0)
    if species.lower() in ["개","강아지","dog"]:
        kcal=weight_kg*30+70; grams=round(kcal/3.5)
    else:
        kcal=60*weight_kg; grams=round(kcal/3.5)
    return grams,max(0,round(grams*0.1))
def recommended_water_ml(weight_kg:float)->int:
    return int(round(weight_kg*60)) if weight_kg>0 else 0
def pet_selector(label="반려동물 선택", key_suffix=""):
    """
    반려동물 선택 Selectbox
    key_suffix : 탭별로 고유 key 부여 (중복 방지)
    """
    pets = st.session_state.pets
    if not pets:
        st.info("먼저 반려동물을 등록해 주세요 (왼쪽 '반려동물 프로필').")
        return None
    opts = {f"{p['name']} ({p['species']})": p for p in pets}
    return opts[st.selectbox(label, list(opts.keys()), key=f"pet_selector_{key_suffix}")]

# ===== 페이지 설정 =====
st.set_page_config(page_title="PetMate",page_icon="🐾",layout="wide")
st.title("🐾 PetMate")

# ===== 로그인 상태 확인 =====
if st.session_state.user is None:
    # 로그인하지 않은 경우 - 로그인/회원가입 탭만 표시
    st.info("PetMate에 오신 것을 환영합니다! 로그인하거나 새 계정을 만들어 시작하세요.")
    
    tab_login = st.tabs(["로그인/회원가입"])[0]
    
    with tab_login:
        st.header("🔐 로그인 & 회원가입")
        users = load_users()

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # ---------------- 로그인 ----------------
        with tab1:
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")

            if st.button("로그인"):
                hashed = hash_password(password)
                if any(u["username"] == username and u["password"] == hashed for u in users):
                    st.session_state.user = username
                    
                    # 🔥 로그인 유지 쿠키 설정 (30일 유지)
                    st.experimental_set_cookie(
                        "petmate_user",
                        username,
                        expires=datetime.now() + timedelta(days=30)
                    )

                    st.success(f"{username}님 로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.") 

        # ---------------- 회원가입 ----------------
        with tab2:
            new_user = st.text_input("새 아이디")
            new_pass = st.text_input("새 비밀번호", type="password")
            if st.button("회원가입"):
                if not new_user.strip() or not new_pass.strip():
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
                elif any(u["username"] == new_user for u in users):
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    users.append({
                        "username": new_user,
                        "password": hash_password(new_pass)
                    })
                    save_users(users)
                    st.success("회원가입 완료! 로그인 탭에서 로그인하세요.")

else:
    # 로그인한 경우 - 모든 탭 표시
    # 상단에 사용자 정보와 로그아웃 버튼 표시
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"👋 안녕하세요, **{st.session_state.user}**님!")
    with col2:
        if st.button("로그아웃"):
            # 세션 초기화
            st.session_state.user = None
            
            # 🔥 쿠키 삭제
            st.experimental_delete_cookie("petmate_user")

            st.rerun()
    
    st.divider()

    # 메인 탭들 - **수정: '건강 추이' 탭 추가**
    tab_dash, tab_health_trends, tab_profile, tab_feed, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
        "대시보드", "건강 추이", "반려동물 프로필", "사료/급수 기록", "복약 알림", "병원 일정", "위험 정보 검색", "데이터 관리"
    ])

    # ============================
    # 📊 대시보드
    # ============================
    with tab_dash:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key_suffix="dash")
        if pet:
            col1,col2,col3 = st.columns(3)
            today_date = local_today()
            today_iso = today_date.isoformat()
            
            with col1:
                st.subheader("기본 정보")
                st.write(f"**이름**: {pet['name']}")
                st.write(f"**종**: {pet['species']}")
                st.write(f"**체중**: {pet.get('weight_kg','-')} kg")
                if pet.get("birth"): st.write(f"**생일**: {pet['birth']}")
                if pet.get("notes"): st.caption(pet["notes"])
                if pet.get("photo_path") and os.path.exists(pet["photo_path"]):
                    st.image(pet["photo_path"],width=150)
            with col2:
                grams,snack_limit = recommended_food_grams(pet["species"],float(pet.get("weight_kg",0) or 0))
                eaten = feed_df[(feed_df["pet_id"]==pet["id"]) & (feed_df["date"]==today_iso)]["amount_g"].sum()
                st.subheader("사료/간식 권장량")
                st.write(f"권장: {grams} g/일 / 간식 상한: {snack_limit} g")
                st.progress(min(1.0,eaten/grams if grams else 0),text=f"오늘 섭취: {int(eaten)} g")
            with col3:
                wml = recommended_water_ml(float(pet.get("weight_kg",0) or 0))
                drank = water_df[(water_df["pet_id"]==pet["id"]) & (water_df["date"]==today_iso)]["amount_ml"].sum()
                st.subheader("물 권장량")
                st.write(f"권장: {wml} ml/일")
                st.progress(min(1.0,drank/wml if wml else 0),text=f"오늘 급수: {int(drank)} ml")

            # ---------------------------
            # 기존 대시보드 차트 (사료, 물)
            # ---------------------------
            st.markdown("## 📈 최근 7일 추이")
            today_chart = local_today()
            last7 = [(today_chart - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
            
            feed_chart = (
                feed_df[(feed_df["pet_id"] == pet["id"]) & (feed_df["date"].isin(last7))]
                .groupby("date")["amount_g"]
                .sum()
                .reindex(last7, fill_value=0)
            )
            st.subheader("🍽️ 사료 섭취량")
            st.line_chart(feed_chart)
            
            water_chart = (
                water_df[(water_df["pet_id"] == pet["id"]) & (water_df["date"].isin(last7))]
                .groupby("date")["amount_ml"]
                .sum()
                .reindex(last7, fill_value=0)
            )
            st.subheader("💧 물 섭취량")
            st.bar_chart(water_chart)

            # ============================
            # 🧩 고급 데이터 분석 기능 (일부만 남김)
            # ============================
            st.markdown("## 🧩 고급 데이터 분석 기능")

            # ---------------------------
            # 0) 기간 선택 (비교 차트를 위해 유지)
            # ---------------------------
            period = st.selectbox(
                "📅 비교 조회 기간 선택",
                ("7일", "14일", "30일"),
                index=0,
                key="dash_period_select"
            )

            days = int(period.replace("일", ""))
            date_range = [(today_chart - timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]


            # ========================================================
            # 1) 오늘 섭취량 도넛 차트
            # ========================================================
            st.subheader("🥣 오늘 섭취량 도넛 차트")

            eaten = feed_df[(feed_df["pet_id"]==pet["id"]) & (feed_df["date"]==today_iso)]["amount_g"].sum()
            grams, snack_limit = recommended_food_grams(pet["species"], float(pet.get("weight_kg", 0)))

            import matplotlib.pyplot as plt

            fig, ax = plt.subplots()

            remaining = max(grams - eaten, 0)

            ax.pie(
                [eaten, remaining],
                labels=[f"먹은양 {eaten}g", f"남은양 {remaining}g"],
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops={'width': 0.35}
            )

            st.pyplot(fig)


            # ========================================================
            # 2) 병원 일정 — 캘린더 UI
            # ========================================================
            st.subheader("🗓️ 병원 일정")

            hosp_pet = [e for e in st.session_state.hospital_events if e["pet_id"] == pet["id"]]

            if hosp_pet:
                cal_data = []
                for ev in hosp_pet:
                    d = datetime.fromisoformat(ev["dt"]).date()
                    cal_data.append({"날짜": d, "제목": ev["title"], "장소": ev.get("place", "")})

                cal_df = pd.DataFrame(cal_data).sort_values("날짜")
                st.dataframe(cal_df, use_container_width=True)
            else:
                st.info("등록된 병원 일정이 없습니다.")


            # ========================================================
            # 3) 체중 기록 + 체중 변화 그래프
            # (새 '건강 추이' 탭으로 이동)
            # ========================================================


            # ========================================================
            # 4) 여러 마리 비교 (사료 섭취량)
            # ========================================================
            st.subheader("🐾 여러 반려동물 비교 (사료 섭취량)")

            if len(st.session_state.pets) >= 2:
                all_pets = st.multiselect(
                    "비교할 반려동물 선택",
                    [f"{p['name']} ({p['id']})" for p in st.session_state.pets],
                    key="multiselect_compare"
                )

                if all_pets:
                    compare_data = {}
                    for opt in all_pets:
                        # (name) (id) 형식에서 id 추출
                        pid = opt.split("(")[-1].replace(")", "")
                        name = opt.split("(")[0].strip()

                        f = feed_df[(feed_df["pet_id"] == pid) & (feed_df["date"].isin(date_range))] \
                            .groupby("date")["amount_g"].sum().reindex(date_range, fill_value=0)

                        compare_data[name] = f.values

                    chart_df = pd.DataFrame(compare_data, index=date_range)
                    st.line_chart(chart_df)
                else:
                    st.info("비교할 동물을 선택하세요.")
            else:
                st.info("2마리 이상 등록해야 비교가 가능합니다.")


    # ===== 건강 추이 (NEW TAB) =====
    with tab_health_trends:
        st.header("📈 건강 추이 분석")
        pet = pet_selector(key_suffix="health_trends")
        if pet:
            today_date = local_today()

            # ========================================================
            # 1) 체중 기록 + 체중 변화 그래프
            # ========================================================
            st.subheader("⚖️ 체중 기록 및 변화 추이")

            # 체중 입력
            with st.form("weight_form_health_trends", key="weight_form_health_trends"):
                col_w1, col_w2 = st.columns([1, 4])
                with col_w1:
                    new_weight = st.number_input("오늘 체중 (kg):", min_value=0.0, step=0.1, key="new_weight_health_trends")
                
                ok_w = st.form_submit_button("저장")
                if ok_w:
                    rec = pd.DataFrame({
                        "log_id": [str(uuid.uuid4())],
                        "pet_id": [pet["id"]],
                        "date": [today_date.isoformat()],
                        "weight": [new_weight]
                    })
                    # 전역 weight_df 업데이트 및 파일 저장
                    global weight_df
                    weight_df = pd.concat([weight_df, rec], ignore_index=True)
                    weight_df.to_csv(WEIGHT_FILE, index=False)
                    st.success("체중이 기록되었습니다!")
            
            # 체중 그래프
            w_pet = weight_df[weight_df["pet_id"] == pet["id"]].sort_values("date")
            if not w_pet.empty:
                w_chart = w_pet.set_index("date")["weight"]
                st.line_chart(w_chart)
                
                st.caption("✅ 체중 변화 기록")
                st.dataframe(w_pet[["date", "weight"]].sort_values("date", ascending=False), hide_index=True)
            else:
                st.info("아직 체중 기록이 없습니다.")
            
            st.divider()

            # ========================================================
            # 2) 복약 스케줄 타임라인 (향후 7일)
            # ========================================================
            st.subheader("💊 향후 7일 복약 스케줄")
            
            meds_pet = [m for m in st.session_state.med_schedule if m["pet_id"] == pet["id"]]
            
            if meds_pet:
                all_events = []
                # 오늘부터 7일간의 복약 스케줄 생성
                for i in range(7):
                    target_date = today_date + timedelta(days=i)
                    for m in meds_pet:
                        # 스케줄 활성 기간 확인
                        is_active = True
                        if m.get("start") and target_date < date.fromisoformat(m["start"]): is_active = False
                        if m.get("end") and target_date > date.fromisoformat(m["end"]): is_active = False
                            
                        if is_active:
                            for t in m.get("times", []):
                                all_events.append({
                                    "날짜": target_date.isoformat(),
                                    "약": m["drug"],
                                    "시간": t,
                                    "용량": f"{m.get('dose', '')}{m.get('unit', '')}"
                                })

                if all_events:
                    med_df = pd.DataFrame(all_events).sort_values(["날짜", "시간"])
                    med_df['날짜'] = med_df['날짜'].apply(lambda x: "오늘" if x == today_date.isoformat() else x[5:])
                    st.dataframe(med_df, use_container_width=True, hide_index=True)
                else:
                    st.info("향후 7일간 등록된 복약 스케줄이 없습니다.")
            else:
                st.info("등록된 복약 스케줄이 없습니다 (복약 알림 탭에서 등록하세요).")


    # ===== 반려동물 프로필 =====
    with tab_profile:
        st.header("🐶 반려동물 프로필")
        st.subheader("등록하기")
        with st.form("pet_form",clear_on_submit=True):
            name = st.text_input("이름*")
            species = st.selectbox("종*",["개","고양이","기타"],index=0)
            breed = st.text_input("품종 (선택)")
            birth = st.date_input("생일 (선택)",value=None)
            weight = st.number_input("체중(kg)",min_value=0.0,step=0.1,value=0.0)
            notes = st.text_area("메모",placeholder="특이사항, 알레르기 등")
            photo_upload = st.file_uploader("프로필 사진 (선택)",type=["jpg","png","jpeg"])
            submitted = st.form_submit_button("추가")
            if submitted:
                photo_path = ""
                if photo_upload:
                    photo_filename = f"{uuid.uuid4()}_{photo_upload.name}"
                    photo_path = os.path.join(PHOTO_DIR,photo_filename)
                    with open(photo_path,"wb") as f: f.write(photo_upload.read())
                new_pet = {"id":str(uuid.uuid4()),"name":name.strip(),"species":species,
                           "breed":breed.strip(),"birth":birth.isoformat() if birth else "",
                           "weight_kg":float(weight),"notes":notes.strip(),"photo_path":photo_path}
                if not new_pet["name"]:
                    st.error("이름은 필수입니다.")
                else:
                    st.session_state.pets.append(new_pet)
                    save_json(PET_FILE,st.session_state.pets)
                    st.success(f"{new_pet['name']} 등록 완료")

        st.subheader("목록/편집")
        if not st.session_state.pets: st.info("등록된 반려동물이 없습니다.")
        else:
            for p in st.session_state.pets:
                with st.expander(f"{p['name']} ({p['species']})"):
                    colA,colB = st.columns([2,1])
                    with colA:
                        p["name"] = st.text_input("이름",value=p["name"],key=f"name_{p['id']}")
                        p["species"] = st.selectbox("종",["개","고양이","기타"],
                            index=["개","고양이","기타"].index(p["species"]) if p["species"] in ["개","고양이","기타"] else 2,
                            key=f"species_{p['id']}")
                        p["breed"] = st.text_input("품종",value=p.get("breed",""),key=f"breed_{p['id']}")
                        p["birth"] = st.text_input("생일(YYYY-MM-DD)",value=p.get("birth",""),key=f"birth_{p['id']}")
                        p["weight_kg"] = st.number_input("체중(kg)",value=float(p.get("weight_kg",0.0)),
                            step=0.1,key=f"weight_{p['id']}")
                        p["notes"] = st.text_area("메모",value=p.get("notes",""),key=f"notes_{p['id']}")
                        new_photo = st.file_uploader("프로필 사진 변경",type=["jpg","png","jpeg"],key=f"photo_{p['id']}")
                        if new_photo:
                            photo_filename = f"{uuid.uuid4()}_{new_photo.name}"
                            photo_path = os.path.join(PHOTO_DIR,photo_filename)
                            with open(photo_path,"wb") as f: f.write(new_photo.read())
                            p["photo_path"] = photo_path
                    with colB:
                        if st.button("저장",key=f"save_{p['id']}"):
                            save_json(PET_FILE,st.session_state.pets); st.success("저장 완료")
                        if st.button("삭제",key=f"del_{p['id']}"):
                            st.session_state.pets = [x for x in st.session_state.pets if x["id"]!=p["id"]]
                            save_json(PET_FILE,st.session_state.pets); st.warning("삭제했습니다.")

    # ===== 사료/급수 기록 =====
    with tab_feed:
        st.header("🍽️ 사료/급수 기록")
        pet = pet_selector(key_suffix="feed")
        if pet:
            with st.form("feed_water_form",clear_on_submit=True):
                c1,c2 = st.columns(2)
                with c1:
                    food_g = st.number_input("사료/간식 섭취량 (g)",min_value=0,step=5)
                    food_memo = st.text_input("사료 메모(선택)")
                with c2:
                    water_ml = st.number_input("급수량 (ml)",min_value=0,step=10)
                    water_memo = st.text_input("물 메모(선택)")
                submitted = st.form_submit_button("💾 오늘 기록 저장")
                if submitted:
                    today = local_today().isoformat()
                    global feed_df, water_df # 전역 변수 사용 명시
                    if food_g>0:
                        new_food = pd.DataFrame({"log_id":[str(uuid.uuid4())],"pet_id":[pet["id"]],
                                                 "date":[today],"amount_g":[int(food_g)],"memo":[food_memo.strip()]})
                        feed_df = pd.concat([feed_df,new_food],ignore_index=True)
                    if water_ml>0:
                        new_water = pd.DataFrame({"log_id":[str(uuid.uuid4())],"pet_id":[pet["id"]],
                                                  "date":[today],"amount_ml":[int(water_ml)],"memo":[water_memo.strip()]})
                        water_df = pd.concat([water_df,new_water],ignore_index=True)
                    save_csv(FEED_FILE,feed_df); save_csv(WATER_FILE,water_df)
                    st.success("✅ 오늘 기록이 저장되었습니다.")

    # ===== 복약 알림 =====
    with tab_med:
        st.header("💊 복약 스케줄")
        pet = pet_selector(key_suffix="med")
        if pet:
            st.subheader("새 복약 스케줄 추가")
            with st.form("med_form",clear_on_submit=True):
                drug = st.text_input("약 이름*")
                dose = st.text_input("용량(예: 5)")
                unit = st.text_input("단위(예: mg, 정 등)")
                times_str = st.text_input("복용 시간들(HH:MM, 콤마로 구분)",placeholder="08:00, 20:00")
                c1,c2 = st.columns(2)
                with c1: start = st.date_input("시작일",value=local_today())
                with c2: end = st.date_input("종료일(선택)",value=None)
                notes = st.text_area("메모")
                ok = st.form_submit_button("추가")
                if ok:
                    rec = {"id":str(uuid.uuid4()),"pet_id":pet["id"],"drug":drug.strip(),
                           "dose":dose.strip(),"unit":unit.strip(),
                           "times":[t.strip() for t in times_str.split(",") if t.strip()],
                           "start":start.isoformat() if start else "",
                           "end":end.isoformat() if end else "",
                           "notes":notes.strip()}
                    if not rec["drug"] or not rec["times"]:
                        st.error("약 이름과 시간은 필수입니다.")
                    else:
                        st.session_state.med_schedule.append(rec)
                        save_json(MED_FILE,st.session_state.med_schedule)
                        st.success("추가 완료")

            st.subheader("스케줄 목록/삭제")
            meds = [m for m in st.session_state.med_schedule if m["pet_id"]==pet["id"]]
            if not meds: st.info("등록된 스케줄이 없습니다.")
            else:
                for m in meds:
                    with st.expander(f"{m['drug']} {m['dose']}{m['unit']} | {', '.join(m.get('times', []))}"):
                        st.write(f"기간: {m.get('start','')} ~ {m.get('end','') or '지속'}")
                        if m.get("notes"): st.caption(m["notes"])
                        if st.button("이 스케줄 삭제",key=f"med_del_{m['id']}"):
                            st.session_state.med_schedule = [x for x in st.session_state.med_schedule if x["id"]!=m["id"]]
                            save_json(MED_FILE,st.session_state.med_schedule)
                            st.warning("삭제했습니다.")
            st.info("알림은 앱 내 표시만 제공됩니다. 시스템 알림이 필요하면 iCal 내보내기/캘린더 연동을 추후 추가하세요.")

    # ===== 병원 일정 =====
    with tab_hosp:
        st.header("🏥 병원 일정 관리")
        pet = pet_selector(key_suffix="hosp")
        if pet:
            st.subheader("일정 추가")
            with st.form("hosp_form",clear_on_submit=True):
                title = st.text_input("제목*")
                dt_col1,dt_col2 = st.columns(2)
                with dt_col1: d = st.date_input("날짜",value=local_today())
                with dt_col2: t = st.time_input("시간",value=time(hour=10,minute=0))
                place = st.text_input("장소")
                notes = st.text_area("메모")
                ok = st.form_submit_button("추가")
                if ok:
                    dt_iso = datetime.combine(d,t).isoformat()
                    rec = {"id":str(uuid.uuid4()),"pet_id":pet["id"],"title":title.strip(),
                           "dt":dt_iso,"place":place.strip(),"notes":notes.strip()}
                    if not rec["title"]: st.error("제목은 필수입니다.")
                    else:
                        st.session_state.hospital_events.append(rec)
                        save_json(HOSP_FILE,st.session_state.hospital_events)
                        st.success("추가 완료")

            st.subheader("다가오는 일정")
            upcoming = [e for e in st.session_state.hospital_events if e["pet_id"]==pet["id"]]
            upcoming = sorted(upcoming,key=lambda x: x["dt"])
            if not upcoming: st.info("등록된 일정이 없습니다.")
            else:
                for e in upcoming:
                    dt_kst = datetime.fromisoformat(e["dt"]).astimezone(tz.gettz("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
                    st.write(f"**{dt_kst}** · {e['title']} @ {e.get('place','')}")
                    if e.get("notes"): st.caption(e["notes"])
                    if st.button("삭제",key=f"evt_del_{e['id']}"):
                        st.session_state.hospital_events = [x for x in st.session_state.hospital_events if x["id"]!=e["id"]]
                        save_json(HOSP_FILE,st.session_state.hospital_events)
                        st.warning("삭제했습니다.")

    # ===== 위험 정보 검색 =====
    with tab_risk:
        st.header("⚠️ 위험 음식/식물/물품 검색")
        q = st.text_input("검색어",placeholder="예: 초콜릿, 양파 …")

        # 🔹 안전장치 추가
        db = pd.DataFrame(st.session_state.unsafe_db)
        for col in ["category", "risk"]:
            if col not in db.columns:
                db[col] = "기타"   # 기본값

        view = db[db["name"].str.contains(q,case=False,na=False)] if q else db
        st.dataframe(view.sort_values(["category","risk"]))

        with st.expander("항목 추가/수정"):
            st.caption("간단한 내부 DB입니다. 필요 시 직접 업데이트하세요.")
            with st.form("unsafe_add",clear_on_submit=True):
                cat = st.selectbox("분류",["음식","식물","물품"])
                nm = st.text_input("이름")
                rk = st.selectbox("위험도",["주의","중간-고위험","고위험"])
                why = st.text_area("이유/설명")
                ok = st.form_submit_button("추가")
                if ok:
                    st.session_state.unsafe_db.append({
                        "category":cat,
                        "name":nm.strip(),
                        "risk":rk,
                        "why":why.strip()
                    })
                    save_json(UNSAFE_FILE,st.session_state.unsafe_db)
                    st.success("추가했습니다.")

    # ===== 데이터 관리 =====
    with tab_data:
        st.header("🗂️ 데이터 관리/백업")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("사료/급수 로그 초기화"):
                save_csv(FEED_FILE,pd.DataFrame(columns=feed_cols))
                save_csv(WATER_FILE,pd.DataFrame(columns=water_cols))
                st.success("초기화 완료")
        with c2:
            if st.button("프로필/복약/일정/DB 초기화"):
                save_json(PET_FILE,[]); save_json(MED_FILE,[])
                save_json(HOSP_FILE,[]); save_json(UNSAFE_FILE,[])
                st.success("초기화 완료")

        if st.button("👥 계정 삭제", key="final_account_delete"):
            save_json(USER_FILE, [])       # users.json 파일 비우기
            st.session_state.user = None   # 혹시 로그인 중이면 로그아웃 처리
            st.experimental_delete_cookie("petmate_user")
            st.success("✅ 모든 회원 계정이 삭제되었습니다.")

# ===== 푸터 =====
st.divider()
