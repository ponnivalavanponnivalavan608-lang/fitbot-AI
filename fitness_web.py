import os
import time
import streamlit as st
from google import genai

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
MODEL   = "gemini-3.6-flash"   # change if needed
KB_FILE = "fitness-bot.txt"

st.set_page_config(
    page_title="FitBot AI",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family:'Poppins',sans-serif; }

.stApp {
    background: linear-gradient(-45deg,#0f2027,#203a43,#2c5364,#0f2027);
    background-size:400% 400%;
    animation: bgAnim 20s ease infinite;
}
@keyframes bgAnim {
    0%{background-position:0% 50%}
    50%{background-position:100% 50%}
    100%{background-position:0% 50%}
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0d1b2a 0%,#1b3a4b 100%);
    border-right:1px solid rgba(67,233,123,.2);
}

/* Hero */
.hero{text-align:center;padding:1rem 0 .5rem;}
.hero h1{
    font-size:2.8rem;font-weight:800;
    background:linear-gradient(90deg,#43e97b,#38f9d7,#43e97b);
    background-size:200% auto;
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    animation:shine 4s linear infinite;
}
@keyframes shine{to{background-position:200% center}}
.hero p{color:#cbd5e1;font-size:1rem;margin-top:.2rem;}

/* Pills */
.pill-row{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin:.5rem 0 1rem;}
.pill{
    background:rgba(67,233,123,.12);
    border:1px solid rgba(67,233,123,.35);
    color:#43e97b;padding:5px 14px;border-radius:999px;
    font-size:.8rem;font-weight:600;
}

/* Cards */
.card{
    background:rgba(255,255,255,.05);
    border:1px solid rgba(67,233,123,.2);
    border-radius:16px;padding:1.2rem;margin-bottom:1rem;
    animation:fadeUp .5s ease;
}
.card h3{color:#43e97b;margin:0 0 .4rem;}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* Metric boxes */
.metric-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1rem;}
.metric{
    flex:1;min-width:120px;
    background:rgba(67,233,123,.1);
    border:1px solid rgba(67,233,123,.25);
    border-radius:12px;padding:.8rem;text-align:center;
}
.metric .val{font-size:1.6rem;font-weight:700;color:#38f9d7;}
.metric .lbl{font-size:.75rem;color:#94a3b8;}

/* Buttons */
.stButton>button{
    border-radius:10px;
    border:1px solid rgba(67,233,123,.4);
    background:rgba(67,233,123,.08);
    color:#e2fff0;font-weight:600;
    transition:all .25s ease;
}
.stButton>button:hover{
    background:linear-gradient(90deg,#43e97b,#38f9d7);
    color:#05221a;border-color:transparent;
    transform:translateY(-2px);
    box-shadow:0 6px 16px rgba(67,233,123,.35);
}

/* Chat bubbles */
[data-testid="stChatMessage"]{animation:fadeUp .3s ease;border-radius:14px;margin-bottom:6px;}

/* Water circles */
.water-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:.5rem;}
.w-glass{
    width:34px;height:34px;border-radius:50%;
    border:2px solid #38f9d7;display:flex;align-items:center;
    justify-content:center;font-size:1rem;cursor:pointer;
    transition:background .2s;
}
.w-full{background:rgba(56,249,215,.35);}
.w-empty{background:transparent;}

footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE DEFAULTS
# ─────────────────────────────────────────────
defaults = {
    "messages":    [],
    "chat":        None,
    "water":       0,
    "profile":     {},
    "page":        "💬 Chat",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💪 FitBot AI")
    st.markdown("---")

    # API key
    API_KEY = os.getenv("GEMINI_API_KEY") or st.text_input(
        "🔑 Gemini API Key", type="password", placeholder="Paste your key…"
    )
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["💬 Chat", "👤 My Profile", "📊 BMI Calculator", "💧 Water Tracker"],
        index=["💬 Chat","👤 My Profile","📊 BMI Calculator","💧 Water Tracker"]
              .index(st.session_state.page),
    )
    st.session_state.page = page
    st.markdown("---")

    # Quick questions (only useful in chat)
    if page == "💬 Chat":
        st.markdown("### ⚡ Quick Questions")
        quick_qs = [
            "What makes a healthy lifestyle?",
            "Best workout for beginners?",
            "How much water should I drink?",
            "Tips to stay motivated?",
            "How much protein do I need?",
        ]
        picked = None
        for q in quick_qs:
            if st.button(q, use_container_width=True):
                picked = q
        st.markdown("---")
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat     = None
            st.rerun()

# ─────────────────────────────────────────────
#  KNOWLEDGE BASE
# ─────────────────────────────────────────────
@st.cache_data
def load_kb(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

kb = load_kb(KB_FILE)

# ─────────────────────────────────────────────
#  BUILD SYSTEM PROMPT (injects profile if set)
# ─────────────────────────────────────────────
def build_prompt():
    p = st.session_state.profile
    profile_block = ""
    if p:
        profile_block = f"""
User profile:
- Name: {p.get('name','Not set')}
- Age: {p.get('age','Not set')}
- Gender: {p.get('gender','Not set')}
- Fitness level: {p.get('level','Not set')}
- Goal: {p.get('goal','Not set')}
Use this profile to personalise your answers when relevant.
"""
    return f"""
You are a friendly fitness instructor with 10 years of experience.
Answer questions politely, clearly, and in a motivating tone.
{profile_block}
Rules:
1. Answer ONLY using the knowledge base (KB) below.
2. If a question is not in the KB, say: "I'm sorry, I don't have that information."
3. Never make up facts or give medical diagnoses.

KB:
{kb}
"""

# ─────────────────────────────────────────────
#  HELPER — send message (fresh client every time)
# ─────────────────────────────────────────────
def send_message(user_text):
    """
    Build a fresh Gemini client + chat on every call,
    passing the full conversation history so context is kept.
    This avoids the 'client has been closed' error.
    """
    client = genai.Client(api_key=API_KEY)
    chat   = client.chats.create(
        model=MODEL,
        config={"system_instruction": build_prompt()},
    )
    # replay previous turns so the model has context
    history = st.session_state.messages[:-1]   # exclude the user msg just appended
    for msg in history:
        if msg["role"] == "user":
            chat.send_message(msg["content"])
    return chat.send_message(user_text).text

# ─────────────────────────────────────────────
#  PAGE: CHAT
# ─────────────────────────────────────────────
if page == "💬 Chat":
    st.markdown("""
    <div class="hero">
        <h1>💪 FitBot AI</h1>
        <p>Your personal AI-powered fitness coach</p>
    </div>
    <div class="pill-row">
        <span class="pill">🥗 Nutrition</span>
        <span class="pill">🏋️ Workouts</span>
        <span class="pill">💧 Hydration</span>
        <span class="pill">😴 Recovery</span>
        <span class="pill">🔥 Motivation</span>
    </div>
    """, unsafe_allow_html=True)

    if not API_KEY:
        st.info("👈 Enter your Gemini API key in the sidebar to start chatting.")
    elif not kb:
        st.error("❌ `fitness-bot.txt` not found. Place it in the same folder as this script.")
    else:
        # show history
        for msg in st.session_state.messages:
            av = "🧑" if msg["role"] == "user" else "💪"
            with st.chat_message(msg["role"], avatar=av):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask me anything about fitness…") or picked

        if user_input:
            st.session_state.messages.append({"role":"user","content":user_input})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar="💪"):
                ph = st.empty()
                ph.markdown("💭 _typing…_")
                try:
                    answer = send_message(user_input)
                except Exception as e:
                    answer = f"Sorry, something went wrong: {e}"

                shown = ""
                for ch in answer:
                    shown += ch
                    if len(shown) % 5 == 0:
                        ph.markdown(shown + "▌")
                        time.sleep(0.004)
                ph.markdown(answer)

            st.session_state.messages.append({"role":"assistant","content":answer})

# ─────────────────────────────────────────────
#  PAGE: MY PROFILE
# ─────────────────────────────────────────────
elif page == "👤 My Profile":
    st.markdown('<div class="hero"><h1>👤 My Profile</h1><p>Personalise your fitness experience</p></div>', unsafe_allow_html=True)

    p = st.session_state.profile

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name   = st.text_input("Name",   value=p.get("name",""))
            age    = st.number_input("Age",  min_value=10, max_value=100, value=int(p.get("age",25)))
            gender = st.selectbox("Gender",  ["Prefer not to say","Male","Female","Other"],
                                  index=["Prefer not to say","Male","Female","Other"].index(p.get("gender","Prefer not to say")))
        with col2:
            level  = st.selectbox("Fitness Level", ["Beginner","Intermediate","Advanced"],
                                  index=["Beginner","Intermediate","Advanced"].index(p.get("level","Beginner")))
            goal   = st.selectbox("Fitness Goal",
                                  ["Lose weight","Build muscle","Stay healthy","Improve endurance","Increase flexibility"],
                                  index=["Lose weight","Build muscle","Stay healthy","Improve endurance","Increase flexibility"].index(
                                      p.get("goal","Stay healthy")))

        submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)
        if submitted:
            st.session_state.profile = {
                "name":name,"age":age,"gender":gender,
                "level":level,"goal":goal,
            }
            st.session_state.chat = None   # rebuild prompt with new profile
            st.success("✅ Profile saved! The chatbot will now personalise its answers.")

    if st.session_state.profile:
        p = st.session_state.profile
        st.markdown(f"""
        <div class="card">
            <h3>📋 Current Profile</h3>
            <div class="metric-row">
                <div class="metric"><div class="val">{p.get('age','—')}</div><div class="lbl">Age</div></div>
                <div class="metric"><div class="val">{p.get('level','—')}</div><div class="lbl">Level</div></div>
                <div class="metric"><div class="val">{p.get('goal','—')}</div><div class="lbl">Goal</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  PAGE: BMI CALCULATOR
# ─────────────────────────────────────────────
elif page == "📊 BMI Calculator":
    st.markdown('<div class="hero"><h1>📊 BMI Calculator</h1><p>Know your numbers — estimates only, not medical advice</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, step=0.5)
        height_cm = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
    with col2:
        age_bmi   = st.number_input("Age", min_value=10, max_value=100, value=25)
        gender_bmi= st.selectbox("Gender", ["Male","Female"])

    if st.button("⚡ Calculate", use_container_width=True):
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)

        if bmi < 18.5:
            cat, col = "Underweight", "#f59e0b"
        elif bmi < 25:
            cat, col = "Normal weight", "#43e97b"
        elif bmi < 30:
            cat, col = "Overweight", "#f97316"
        else:
            cat, col = "Obese", "#ef4444"

        # BMR (Mifflin-St Jeor)
        if gender_bmi == "Male":
            bmr = 10*weight_kg + 6.25*height_cm - 5*age_bmi + 5
        else:
            bmr = 10*weight_kg + 6.25*height_cm - 5*age_bmi - 161

        tdee = round(bmr * 1.55)   # moderate activity estimate

        st.markdown(f"""
        <div class="card">
            <h3>Your Results</h3>
            <div class="metric-row">
                <div class="metric">
                    <div class="val" style="color:{col}">{bmi:.1f}</div>
                    <div class="lbl">BMI</div>
                </div>
                <div class="metric">
                    <div class="val" style="color:{col}">{cat}</div>
                    <div class="lbl">Category</div>
                </div>
                <div class="metric">
                    <div class="val">{int(bmr)}</div>
                    <div class="lbl">BMR (kcal/day)</div>
                </div>
                <div class="metric">
                    <div class="val">{tdee}</div>
                    <div class="lbl">Est. Daily Calories</div>
                </div>
            </div>
            <p style="color:#94a3b8;font-size:.8rem;margin-top:.5rem;">
            ⚠️ These are estimates. Consult a healthcare professional for personalised advice.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # BMI progress bar
        pct = min(int((bmi / 40) * 100), 100)
        st.markdown(f"**BMI scale (0 – 40)**")
        st.progress(pct)

# ─────────────────────────────────────────────
#  PAGE: WATER TRACKER
# ─────────────────────────────────────────────
elif page == "💧 Water Tracker":
    st.markdown('<div class="hero"><h1>💧 Water Tracker</h1><p>Stay hydrated — aim for 8 glasses a day</p></div>', unsafe_allow_html=True)

    GOAL = 8
    glasses = st.session_state.water

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Add a glass", use_container_width=True):
            if glasses < GOAL:
                st.session_state.water += 1
                glasses += 1
    with col2:
        if st.button("➖ Remove a glass", use_container_width=True):
            if glasses > 0:
                st.session_state.water -= 1
                glasses -= 1
    with col3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.water = 0
            glasses = 0

    pct = int((glasses / GOAL) * 100)
    if glasses == GOAL:
        msg, color = "🎉 Goal reached! Great job!", "#43e97b"
    elif glasses >= 6:
        msg, color = "💧 Almost there, keep going!", "#38f9d7"
    elif glasses >= 3:
        msg, color = "👍 Good progress, keep drinking!", "#f59e0b"
    else:
        msg, color = "🥤 Start drinking water!", "#94a3b8"

    st.markdown(f"""
    <div class="card">
        <h3>Today's Intake</h3>
        <div class="metric-row">
            <div class="metric">
                <div class="val" style="color:{color}">{glasses}/{GOAL}</div>
                <div class="lbl">Glasses</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{color}">{glasses*250} ml</div>
                <div class="lbl">Volume</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{color}">{pct}%</div>
                <div class="lbl">Goal</div>
            </div>
        </div>
        <p style="color:{color};font-weight:600;">{msg}</p>
    </div>
    """, unsafe_allow_html=True)

    st.progress(pct)

    # Visual glasses
    icons = "".join(
        f'<div class="w-glass {"w-full" if i < glasses else "w-empty"}">{"💧" if i < glasses else "🥤"}</div>'
        for i in range(GOAL)
    )
    st.markdown(f'<div class="water-row">{icons}</div>', unsafe_allow_html=True)