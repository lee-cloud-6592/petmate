# PetMate: 반려동물 통합 케어 앱 (Streamlit) - 개선 버전
import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib
import plotly.express as px
import plotly.graph_objects as go

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
WEIGHT_FILE = os.path.join(DATA_DIR, "weight_log.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "login_cookie.json")
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

# ===== 쿠키 관련 함수 =====
def save_login_cookie(username):
    """로그인 정보를 쿠키 파일에 저장"""
    cookie_data = {
        "username": username,
        "timestamp": datetime.now().isoformat()
    }
    save_json(COOKIE_FILE, cookie_data)

def load_login_cookie():
    """쿠키 파일에서 로그인 정보 불러오기"""
    cookie = load_json(COOKIE_FILE, None)
    if cookie and "username" in cookie:
        # 쿠키 유효기간 체크 (7일)
        saved_time = datetime.fromisoformat(cookie["timestamp"])
        if datetime.now() - saved_time < timedelta(days=7):
            return cookie["username"]
    return None

def clear_login_cookie():
    """로그인 쿠키 삭제"""
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)

# ===== 초기 세션 =====
if "user" not in st.session_state:
    # 쿠키에서 로그인 정보 복원
    saved_user = load_login_cookie()
    st.session_state.user = saved_user

if "pets" not in st.session_state: st.session_state.pets = load_json(PET_FILE,[])
if "med_schedule" not in st.session_state: st.session_state.med_schedule = load_json(MED_FILE,[])
if "hospital_events" not in st.session_state: st.session_state.hospital_events = load_json(HOSP_FILE,[])
if "unsafe_db" not in st.session_state:
    default_unsafe=[{"category":"음식","name":"초콜릿","risk":"고위험","why":"카카오의 메틸잔틴(테오브로민) 독성"},
                    {"category":"음식","name":"포도/건포도","risk":"고위험","why":"급성 신장손상 보고"}]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE,default_unsafe)

feed_cols=["log_id","pet_id","date","amount_g","memo"]
water_cols=["log_id","pet_id","date","amount_ml","memo"]
weight_cols=["log_id","pet_id","date","weight_kg","memo"]

feed_df = load_csv(FEED_FILE,feed_cols)
water_df = load_csv(WATER_FILE,water_cols)
weight_df = load_csv(WEIGHT_FILE,weight_cols)

def recommended_food_grams(species:str,weight_kg:float)->tuple:
    if weight_kg<=0: return (0,0)
    if species.lower() in ["개","강아지","dog"]:
        kcal=weight_kg*30+70; grams=round(kcal/3.5)
    else:
        kcal=60*weight_kg; grams=round(kcal/3.5)
    return grams,max(0,round(grams*0.1))

def recommended_water_ml(weight_kg:float)->int:
    return int(round(weight_kg*60)) if weight_kg>0 else 0

def pet_selector(label="반려동물 선택", key=None):
    pets=st.session_state.pets
    if not pets:
        st.info("먼저 반려동물을 등록해 주세요 (왼쪽 '반려동물 프로필').")
        return None
    opts={f"{p['name']} ({p['species']})":p for p in pets}
    return opts[st.selectbox(label,list(opts.keys()), key=key)]

# ===== 페이지 설정 =====
st.set_page_config(page_title="PetMate",page_icon="🐾",layout="wide")
st.title("🐾 PetMate")

# ===== 로그인 상태 확인 =====
if not st.session_state.user:
    # 로그인하지 않은 상태 - 로그인/회원가입 탭만 표시
    tab_login = st.tabs(["로그인/회원가입"])[0]
    
    with tab_login:
        st.header("🔐 로그인 & 회원가입")
        st.info("PetMate에 오신 것을 환영합니다! 로그인 후 모든 기능을 이용하실 수 있습니다.")
        
        users = load_users()

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # ---------------- 로그인 ----------------
        with tab1:
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            remember_me = st.checkbox("로그인 상태 유지 (7일)", value=True)
            
            if st.button("로그인"):
                hashed = hash_password(password)
                if any(u["username"] == username and u["password"] == hashed for u in users):
                    st.session_state.user = username
                    if remember_me:
                        save_login_cookie(username)
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
    # 로그인한 상태 - 모든 탭 표시
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(f"안녕하세요, **{st.session_state.user}**님! 👋")
    with col2:
        if st.button("로그아웃"):
            st.session_state.user = None
            clear_login_cookie()
            st.rerun()

    tab_dash, tab_profile, tab_feed, tab_health, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
        "대시보드","반려동물 프로필", "사료/급수 기록","📈 건강 데이터","복약 알림","병원 일정","위험 정보 검색","데이터 관리"
    ])

    # ===== 대시보드 =====
    with tab_dash:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key="dashboard_pet_selector")
        if pet:
            col1,col2,col3 = st.columns(3)
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
                today = local_today().isoformat()
                eaten = feed_df[(feed_df["pet_id"]==pet["id"]) & (feed_df["date"]==today)]["amount_g"].sum()
                st.subheader("사료/간식 권장량")
                st.write(f"권장: {grams} g/일 / 간식 상한: {snack_limit} g")
                st.progress(min(1.0,eaten/grams if grams else 0),text=f"오늘 섭취: {int(eaten)} g")
            with col3:
                wml = recommended_water_ml(float(pet.get("weight_kg",0) or 0))
                drank = water_df[(water_df["pet_id"]==pet["id"]) & (water_df["date"]==today)]["amount_ml"].sum()
                st.subheader("물 권장량")
                st.write(f"권장: {wml} ml/일")
                st.progress(min(1.0,drank/wml if wml else 0),text=f"오늘 급수: {int(drank)} ml")

            # 최근 7일 간단 차트
            st.divider()
            st.subheader("📊 최근 7일 요약")
            
            # 날짜 범위
            end_date = local_today()
            start_date = end_date - timedelta(days=6)
            date_range = pd.date_range(start=start_date, end=end_date)
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # 사료 섭취량 차트
                pet_feed = feed_df[feed_df["pet_id"]==pet["id"]].copy()
                pet_feed["date"] = pd.to_datetime(pet_feed["date"])
                pet_feed = pet_feed[pet_feed["date"] >= pd.Timestamp(start_date)]
                daily_feed = pet_feed.groupby("date")["amount_g"].sum().reindex(date_range, fill_value=0)
                
                fig_feed = go.Figure()
                fig_feed.add_trace(go.Bar(x=daily_feed.index, y=daily_feed.values, name="섭취량"))
                fig_feed.add_hline(y=grams, line_dash="dash", line_color="red", annotation_text="권장량")
                fig_feed.update_layout(title="사료 섭취량 (g)", height=300, showlegend=False)
                st.plotly_chart(fig_feed, use_container_width=True)
            
            with col_chart2:
                # 급수량 차트
                pet_water = water_df[water_df["pet_id"]==pet["id"]].copy()
                pet_water["date"] = pd.to_datetime(pet_water["date"])
                pet_water = pet_water[pet_water["date"] >= pd.Timestamp(start_date)]
                daily_water = pet_water.groupby("date")["amount_ml"].sum().reindex(date_range, fill_value=0)
                
                fig_water = go.Figure()
                fig_water.add_trace(go.Bar(x=daily_water.index, y=daily_water.values, name="급수량", marker_color="lightblue"))
                fig_water.add_hline(y=wml, line_dash="dash", line_color="blue", annotation_text="권장량")
                fig_water.update_layout(title="급수량 (ml)", height=300, showlegend=False)
                st.plotly_chart(fig_water, use_container_width=True)

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
                    
                    # 초기 체중 기록
                    if weight > 0:
                        today = local_today().isoformat()
                        new_weight = pd.DataFrame({
                            "log_id": [str(uuid.uuid4())],
                            "pet_id": [new_pet["id"]],
                            "date": [today],
                            "weight_kg": [float(weight)],
                            "memo": ["초기 등록"]
                        })
                        global weight_df
                        weight_df = pd.concat([weight_df, new_weight], ignore_index=True)
                        save_csv(WEIGHT_FILE, weight_df)
                    
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
                            save_json(PET_FILE,st.session_state.pets)
                            st.success("저장 완료")
                        if st.button("삭제",key=f"del_{p['id']}"):
                            st.session_state.pets = [x for x in st.session_state.pets if x["id"]!=p["id"]]
                            save_json(PET_FILE,st.session_state.pets)
                            st.warning("삭제했습니다.")

    # ===== 사료/급수 기록 =====
    with tab_feed:
        st.header("🍽️ 사료/급수 기록")
        pet = pet_selector(key="feed_pet_selector")
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
                    if food_g>0:
                        new_food = pd.DataFrame({"log_id":[str(uuid.uuid4())],"pet_id":[pet["id"]],
                                                 "date":[today],"amount_g":[int(food_g)],"memo":[food_memo.strip()]})
                        feed_df = pd.concat([feed_df,new_food],ignore_index=True)
                    if water_ml>0:
                        new_water = pd.DataFrame({"log_id":[str(uuid.uuid4())],"pet_id":[pet["id"]],
                                                  "date":[today],"amount_ml":[int(water_ml)],"memo":[water_memo.strip()]})
                        water_df = pd.concat([water_df,new_water],ignore_index=True)
                    save_csv(FEED_FILE,feed_df)
                    save_csv(WATER_FILE,water_df)
                    st.success("✅ 오늘 기록이 저장되었습니다.")

    # ===== 건강 데이터 탭 (새로 추가) =====
    with tab_health:
        st.header("📈 건강 데이터 추적")
        pet = pet_selector(key="health_pet_selector")
        
        if pet:
            # 체중 기록 추가
            st.subheader("📝 체중 기록하기")
            with st.form("weight_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    weight_date = st.date_input("측정 날짜", value=local_today())
                    new_weight = st.number_input("체중 (kg)", min_value=0.0, step=0.1, value=float(pet.get("weight_kg", 0.0)))
                with col2:
                    weight_memo = st.text_area("메모 (선택)", placeholder="건강 상태, 특이사항 등")
                
                if st.form_submit_button("체중 기록 추가"):
                    new_record = pd.DataFrame({
                        "log_id": [str(uuid.uuid4())],
                        "pet_id": [pet["id"]],
                        "date": [weight_date.isoformat()],
                        "weight_kg": [float(new_weight)],
                        "memo": [weight_memo.strip()]
                    })
                    weight_df = pd.concat([weight_df, new_record], ignore_index=True)
                    save_csv(WEIGHT_FILE, weight_df)
                    
                    # 프로필의 체중도 업데이트
                    for p in st.session_state.pets:
                        if p["id"] == pet["id"]:
                            p["weight_kg"] = float(new_weight)
                    save_json(PET_FILE, st.session_state.pets)
                    
                    st.success("✅ 체중 기록이 추가되었습니다!")
                    st.rerun()
            
            st.divider()
            
            # 차트 표시
            st.subheader("📊 데이터 차트")
            
            # 기간 선택
            period = st.selectbox("기간 선택", ["최근 7일", "최근 30일", "최근 3개월", "최근 6개월", "전체"], index=1)
            
            end_date = local_today()
            if period == "최근 7일":
                start_date = end_date - timedelta(days=6)
            elif period == "최근 30일":
                start_date = end_date - timedelta(days=29)
            elif period == "최근 3개월":
                start_date = end_date - timedelta(days=89)
            elif period == "최근 6개월":
                start_date = end_date - timedelta(days=179)
            else:
                start_date = None
            
            # 체중 변화 차트
            st.subheader("⚖️ 체중 변화")
            pet_weight = weight_df[weight_df["pet_id"] == pet["id"]].copy()
            if not pet_weight.empty:
                pet_weight["date"] = pd.to_datetime(pet_weight["date"])
                pet_weight = pet_weight.sort_values("date")
                
                if start_date:
                    pet_weight = pet_weight[pet_weight["date"] >= pd.Timestamp(start_date)]
                
                if not pet_weight.empty:
                    fig_weight = px.line(pet_weight, x="date", y="weight_kg", 
                                        markers=True, title="체중 변화 추이")
                    fig_weight.update_layout(
                        xaxis_title="날짜",
                        yaxis_title="체중 (kg)",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_weight, use_container_width=True)
                    
                    # 통계 표시
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("현재 체중", f"{pet_weight.iloc[-1]['weight_kg']:.1f} kg")
                    with col2:
                        if len(pet_weight) > 1:
                            weight_change = pet_weight.iloc[-1]['weight_kg'] - pet_weight.iloc[0]['weight_kg']
                            st.metric("체중 변화", f"{weight_change:+.1f} kg")
                    with col3:
                        st.metric("평균 체중", f"{pet_weight['weight_kg'].mean():.1f} kg")
                    with col4:
                        st.metric("측정 횟수", f"{len(pet_weight)}회")
                else:
                    st.info("선택한 기간에 체중 기록이 없습니다.")
            else:
                st.info("체중 기록이 없습니다. 위에서 체중을 기록해보세요!")
            
            st.divider()
            
            # 사료 섭취량 차트
            st.subheader("🍽️ 사료 섭취량")
            pet_feed = feed_df[feed_df["pet_id"] == pet["id"]].copy()
            if not pet_feed.empty:
                pet_feed["date"] = pd.to_datetime(pet_feed["date"])
                if start_date:
                    pet_feed = pet_feed[pet_feed["date"] >= pd.Timestamp(start_date)]
                
                if not pet_feed.empty:
                    daily_feed = pet_feed.groupby("date")["amount_g"].sum().reset_index()
                    
                    grams, _ = recommended_food_grams(pet["species"], float(pet.get("weight_kg", 0) or 0))
                    
                    fig_feed = go.Figure()
                    fig_feed.add_trace(go.Bar(x=daily_feed["date"], y=daily_feed["amount_g"], 
                                             name="실제 섭취량", marker_color="lightgreen"))
                    if grams > 0:
                        fig_feed.add_hline(y=grams, line_dash="dash", line_color="red", 
                                          annotation_text=f"권장량 ({grams}g)")
                    fig_feed.update_layout(
                        title="일별 사료 섭취량",
                        xaxis_title="날짜",
                        yaxis_title="섭취량 (g)",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_feed, use_container_width=True)
                    
                    # 통계
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("평균 섭취량", f"{daily_feed['amount_g'].mean():.0f} g/일")
                    with col2:
                        if grams > 0:
                            compliance = (daily_feed['amount_g'].mean() / grams * 100)
                            st.metric("권장량 대비", f"{compliance:.0f}%")
                    with col3:
                        st.metric("기록 일수", f"{len(daily_feed)}일")
                else:
                    st.info("선택한 기간에 사료 기록이 없습니다.")
            else:
                st.info("사료 섭취 기록이 없습니다.")
            
            st.divider()
            
            # 급수량 차트
            st.subheader("💧 급수량")
            pet_water = water_df[water_df["pet_id"] == pet["id"]].copy()
            if not pet_water.empty:
                pet_water["date"] = pd.to_datetime(pet_water["date"])
                if start_date:
                    pet_water = pet_water[pet_water["date"] >= pd.Timestamp(start_date)]
                
                if not pet_water.empty:
                    daily_water = pet_water.groupby("date")["amount_ml"].sum().reset_index()
                    
                    water_ml = recommended_water_ml(float(pet.get("weight_kg", 0) or 0))
                    
                    fig_water = go.Figure()
                    fig_water.add_trace(go.Bar(x=daily_water["date"], y=daily_water["amount_ml"], 
                                             name="실제 급수량", marker_color="lightblue"))
                    if water_ml > 0:
                        fig_water.add_hline(y=water_ml, line_dash="dash", line_color="blue", 
                                          annotation_text=f"권장량 ({water_ml}ml)")
                    fig_water.update_layout(
                        title="일별 급수량",
                        xaxis_title="날짜",
                        yaxis_title="급수량 (ml)",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_water, use_container_width=True)
                    
                    # 통계
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("평균 급수량", f"{daily_water['amount_ml'].mean():.0f} ml/일")
                    with col2:
                        if water_ml > 0:
                            compliance = (daily_water['amount_ml'].mean() / water_ml * 100)
                            st.metric("권장량 대비", f"{compliance:.0f}%")
                    with col3:
                        st.metric("기록 일수", f"{len(daily_water)}일")
                else:
                    st.info("선택한 기간에 급수 기록이 없습니다.")
            else:
                st.info("급수 기록이 없습니다.")
            
            st.divider()
            
            # 복약 기록 통계
            st.subheader("💊 복약 현황")
            pet_meds = [m for m in st.session_state.med_schedule if m["pet_id"] == pet["id"]]
            if pet_meds:
                st.write(f"**등록된 약물: {len(pet_meds)}개**")
                for med in pet_meds:
                    st.write(f"• {med['drug']} - {med['dose']}{med['unit']} ({', '.join(med.get('times', []))})")
            else:
                st.info("등록된 복약 스케줄이 없습니다.")

    # ===== 복약 알림 =====
    with tab_med:
        st.header("💊 복약 스케줄")
        pet = pet_selector(key="med_pet_selector")
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
        pet = pet_selector(key="hosp_pet_selector")
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

        db = pd.DataFrame(st.session_state.unsafe_db)
        for col in ["category", "risk"]:
            if col not in db.columns:
                db[col] = "기타"

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
            if st.button("사료/급수/체중 로그 초기화"):
                save_csv(FEED_FILE,pd.DataFrame(columns=feed_cols))
                save_csv(WATER_FILE,pd.DataFrame(columns=water_cols))
                save_csv(WEIGHT_FILE,pd.DataFrame(columns=weight_cols))
                st.success("초기화 완료")
        with c2:
            if st.button("프로필/복약/일정/DB 초기화"):
                save_json(PET_FILE,[]); save_json(MED_FILE,[])
                save_json(HOSP_FILE,[]); save_json(UNSAFE_FILE,[])
                st.success("초기화 완료")

        if st.button("👥 계정 삭제"):
            save_json(USER_FILE, [])
            st.session_state.user = None
            clear_login_cookie()
            st.success("✅ 모든 회원 계정이 삭제되었습니다.")

# ===== 푸터 =====
st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 샘플. 실제 의료 조언은 수의사와 상담하세요.")
