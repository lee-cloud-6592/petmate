# PetMate: 반려동물 통합 케어 앱 (Streamlit)
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
os.makedirs(PHOTO_DIR, exist_ok=True)
PET_FILE = os.path.join(DATA_DIR, "pets.json")
FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")
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
feed_df = load_csv(FEED_FILE,feed_cols)
water_df = load_csv(WATER_FILE,water_cols)

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
                    st.success(f"{username}님 로그인 성공!")
                    st.rerun()  # 페이지 새로고침
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
            st.session_state.user = None
            st.success("로그아웃 되었습니다.")
            st.rerun()
    
    st.divider()
    
    # 메인 탭들
    tab_dash, tab_profile, tab_feed, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
        "대시보드","반려동물 프로필","사료/급수 기록","복약 알림","병원 일정","위험 정보 검색","데이터 관리"
    ])

    # ===== 대시보드 =====
    with tab_dash:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key_suffix="dash")
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

        if st.button("👥 계정 삭제"):
            save_json(USER_FILE, [])       # users.json 파일 비우기
            st.session_state.user = None   # 혹시 로그인 중이면 로그아웃 처리
            st.success("✅ 모든 회원 계정이 삭제되었습니다.")

# ===== 푸터 =====
st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 샘플. 실제 의료 조언은 수의사와 상담하세요.")




