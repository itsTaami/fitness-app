import streamlit as st
from datetime import datetime
import pandas as pd
import uuid
import hashlib
from supabase_client import supabase
from groq_api import call_groq
from prompts import build_workout_prompt, build_meal_prompt
from helpers import safe_int, safe_float

st.set_page_config(page_title="Level-Up Fitness", layout="wide")

AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.2-90b-text-preview",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
    "gemma2-9b-it"
]

MIN_AGE = 10
MAX_AGE = 120

# -------------------- Simple Password Hash --------------------
def hash_password(password):
    """Simple hash function (not secure for production!)"""
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------- Authentication Functions --------------------
def signup_user(username, password, email=""):
    """Register a new user"""
    try:
        existing = supabase.table("users").select("*").eq("username", username).execute()
        if existing.data:
            return False, "Username already exists"
        
        hashed_pw = hash_password(password)
        result = supabase.table("users").insert({
            "username": username,
            "password": hashed_pw,
            "email": email
        }).execute()
        
        if result.data:
            return True, "Signup successful! Please login."
        return False, "Signup failed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def login_user(username, password):
    """Authenticate user"""
    try:
        hashed_pw = hash_password(password)
        result = supabase.table("users").select("*").eq("username", username).eq("password", hashed_pw).execute()
        
        if result.data:
            user = result.data[0]
            return True, user
        return False, "Invalid username or password"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_user_profile(user_id):
    """Get profile for logged in user"""
    try:
        result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        st.error(f"Error loading profile: {e}")
        return None

def save_user_profile(user_id, profile_data):
    """Save or update user profile"""
    try:
        existing = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            res = supabase.table("profiles").update(profile_data).eq("user_id", user_id).execute()
        else:
            profile_data["user_id"] = user_id
            res = supabase.table("profiles").insert(profile_data).execute()
        
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Error saving profile: {e}")
        return None

# -------------------- Initialize Session State --------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'profile' not in st.session_state:
    st.session_state.profile = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"
if 'nav_expanded' not in st.session_state:
    st.session_state.nav_expanded = False

# -------------------- Navbar Component --------------------
def show_navbar():
    """Display top navigation bar"""
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
    
    with col1:
        st.markdown("## 🏋️ Level-Up Fitness")
    
    # Navigation buttons
    nav_items = {
        "Profile": "profile",
        "AI Workout": "workout", 
        "AI Meal": "meal",
        "Progress": "progress",
        "Settings": "settings"
    }
    
    # Create navigation buttons
    if st.session_state.logged_in:
        with col2:
            if st.button("🏠 Profile", use_container_width=True):
                st.session_state.current_page = "profile"
                st.rerun()
        
        with col3:
            if st.button("💪 Workout", use_container_width=True):
                st.session_state.current_page = "workout"
                st.rerun()
        
        with col4:
            if st.button("🍎 Meal", use_container_width=True):
                st.session_state.current_page = "meal"
                st.rerun()
        
        with col5:
            if st.button("📈 Progress", use_container_width=True):
                st.session_state.current_page = "progress"
                st.rerun()
        
        with col6:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state.current_page = "settings"
                st.rerun()
        
        with col7:
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.profile = None
                st.session_state.current_page = "login"
                st.rerun()
    
    st.markdown("---")  # Separator line

# -------------------- User Info Widget --------------------
def show_user_info():
    """Show user info in a compact widget"""
    if st.session_state.logged_in and st.session_state.profile:
        with st.expander(f"👤 {st.session_state.user['username']}'s Stats", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Weight", f"{st.session_state.profile.get('weight', 0)} kg")
            with col2:
                st.metric("Target Weight", f"{st.session_state.profile.get('target_weight', 0)} kg")
            with col3:
                if st.session_state.profile.get('height'):
                    st.metric("Height", f"{st.session_state.profile.get('height')} cm")

# -------------------- Authentication Pages --------------------
def show_login():
    """Login page"""
    st.title("🔐 Login to Level-Up Fitness")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    success, result = login_user(username, password)
                    if success:
                        st.session_state.user = result
                        st.session_state.logged_in = True
                        st.session_state.profile = get_user_profile(result["id"])
                        st.session_state.current_page = "profile"
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result)
        
        st.markdown("---")
        st.write("Don't have an account?")
        if st.button("Sign Up Instead"):
            st.session_state.current_page = "signup"
            st.rerun()

def show_signup():
    """Signup page"""
    st.title("📝 Create Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("signup_form"):
            username = st.text_input("Choose Username")
            email = st.text_input("Email (optional)")
            password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_btn = st.form_submit_button("Create Account")
            
            if signup_btn:
                if not username or not password:
                    st.error("Username and password are required")
                elif password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    success, message = signup_user(username, password, email)
                    if success:
                        st.success(message)
                        st.session_state.current_page = "login"
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown("---")
        st.write("Already have an account?")
        if st.button("Login Instead"):
            st.session_state.current_page = "login"
            st.rerun()

# -------------------- Main App Pages --------------------
def show_profile():
    """Profile page"""
    st.title("👤 Profile Settings")
    
    if not st.session_state.profile:
        st.session_state.profile = {
            "name": "", 
            "age": 16, 
            "gender": "Prefer not to say", 
            "height": 170, 
            "weight": 60, 
            "target_weight": 60
        }
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name", value=st.session_state.profile.get("name", ""))
            age = st.number_input("Age", min_value=MIN_AGE, max_value=MAX_AGE, 
                                value=safe_int(st.session_state.profile.get("age", 16)))
            gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"], 
                                index=["Prefer not to say", "Male", "Female", "Other"].index(
                                    st.session_state.profile.get("gender", "Prefer not to say")))
        
        with col2:
            height = st.number_input("Height (cm)", 100, 250, 
                                   value=safe_int(st.session_state.profile.get("height", 170)))
            weight = st.number_input("Weight (kg)", 20.0, 300.0, 
                                   value=safe_float(st.session_state.profile.get("weight", 60)))
            target_weight = st.number_input("Target Weight (kg)", 20.0, 300.0, 
                                          value=safe_float(st.session_state.profile.get("target_weight", weight)))
        
        submit_profile = st.form_submit_button("💾 Save Profile", use_container_width=True)
    
    if submit_profile:
        profile_data = {
            "name": name,
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "target_weight": target_weight
        }
        
        saved_profile = save_user_profile(st.session_state.user["id"], profile_data)
        if saved_profile:
            st.session_state.profile = saved_profile
            st.success("✅ Profile saved successfully!")
        else:
            st.error("❌ Failed to save profile")

def show_workout():
    """Workout generator page"""
    st.title("💪 AI Workout Generator")
    
    if not st.session_state.profile or not st.session_state.profile.get("name"):
        st.warning("⚠️ Please fill out your profile first!")
        return
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("workout_form"):
                goal = st.selectbox("Goal", ["General fitness", "Muscle gain", "Fat loss", "Endurance"])
                duration = st.selectbox("Duration", ["20 min", "30 min", "45 min", "60 min"])
                level = st.selectbox("Experience", ["Beginner", "Intermediate", "Advanced"])
                focus = st.selectbox("Focus", ["Full Body", "Upper Body", "Lower Body", "Core"])
                equipment = st.multiselect("Equipment", ["Bodyweight", "Dumbbells", "Bands"], default=["Bodyweight"])
                days = st.slider("Days per week", 2, 6, 3)
                notes = st.text_area("Notes", "")
                generate = st.form_submit_button("🚀 Generate Workout", use_container_width=True)
        
        with col2:
            if st.session_state.profile:
                st.info("### Your Profile")
                st.write(f"**Name:** {st.session_state.profile.get('name', 'Not set')}")
                st.write(f"**Age:** {st.session_state.profile.get('age', 'Not set')}")
                st.write(f"**Weight:** {st.session_state.profile.get('weight', 'Not set')} kg")
                st.write(f"**Height:** {st.session_state.profile.get('height', 'Not set')} cm")
    
    if generate:
        with st.spinner("🤖 Generating your personalized workout plan..."):
            try:
                prompt = build_workout_prompt(
                    st.session_state.profile, goal, duration, level, 
                    focus, equipment, days, notes
                )
                result = call_groq(prompt)
                
                if result.startswith("❌"):
                    st.error(result)
                else:
                    st.success("✅ Workout Generated!")
                    st.markdown("---")
                    st.markdown(result)
                    
                    # Save to database
                    supabase.table("workouts").insert({
                        "user_id": st.session_state.user["id"],
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "plan": result
                    }).execute()
                    
                    # Download button
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📥 Download Workout", 
                            result, 
                            file_name=f"workout_{uuid.uuid4().hex[:8]}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
            except Exception as e:
                st.error(f"❌ Error generating workout: {e}")

def show_meal():
    """Meal plan generator page"""
    st.title("🍎 AI Meal Plan Generator")
    
    if not st.session_state.profile or not st.session_state.profile.get("name"):
        st.warning("⚠️ Please fill out your profile first!")
        return
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("meal_form"):
                goal = st.selectbox("Goal", ["Healthy eating", "Muscle gain", "Energy"])
                diet_type = st.selectbox("Diet Type", ["Balanced", "High Protein", "Vegetarian"])
                meals_per_day = st.selectbox("Meals per day", [3, 4, 5])
                cuisine = st.selectbox("Cuisine", ["Any", "Asian", "Mediterranean", "Japanese"])
                restrictions = st.multiselect("Restrictions", ["None", "Gluten-free", "Dairy-free", "Nut-free"])
                notes = st.text_area("Notes", "")
                generate_meal = st.form_submit_button("🚀 Generate Meal Plan", use_container_width=True)
        
        with col2:
            if st.session_state.profile:
                st.info("### Your Profile")
                st.write(f"**Name:** {st.session_state.profile.get('name', 'Not set')}")
                st.write(f"**Age:** {st.session_state.profile.get('age', 'Not set')}")
                st.write(f"**Weight:** {st.session_state.profile.get('weight', 'Not set')} kg")
                st.write(f"**Height:** {st.session_state.profile.get('height', 'Not set')} cm")
    
    if generate_meal:
        if restrictions == ["None"]:
            restrictions = []
            
        with st.spinner("🤖 Generating your personalized meal plan..."):
            try:
                prompt = build_meal_prompt(
                    st.session_state.profile, goal, diet_type, meals_per_day, 
                    cuisine, restrictions, notes
                )
                result = call_groq(prompt)
                
                if result.startswith("❌"):
                    st.error(result)
                else:
                    st.success("✅ Meal Plan Generated!")
                    st.markdown("---")
                    st.markdown(result)
                    
                    # Save to database
                    supabase.table("meals").insert({
                        "user_id": st.session_state.user["id"],
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "plan": result
                    }).execute()
                    
                    # Download button
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📥 Download Meal Plan", 
                            result, 
                            file_name=f"meal_{uuid.uuid4().hex[:8]}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
            except Exception as e:
                st.error(f"❌ Error generating meal plan: {e}")

def show_progress():
    """Progress tracking page"""
    st.title("📈 Weight Progress Tracker")
    
    if not st.session_state.profile:
        st.warning("⚠️ Please save your profile first to track weight progress.")
        return
    
    try:
        # Load weight logs
        weight_logs = supabase.table("weight_log")\
            .select("*")\
            .eq("user_id", st.session_state.user["id"])\
            .order("date", desc=True)\
            .execute().data
        
        if weight_logs:
            df = pd.DataFrame(weight_logs)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            
            # Display chart
            st.subheader("Weight Trend")
            st.line_chart(df.set_index("date")["weight"])
            
            # Display table
            st.subheader("Recent Entries")
            display_df = df[["date", "weight"]].copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df = display_df.sort_values("date", ascending=False)
            st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("📊 No weight data yet. Add your first weight entry below.")
            
    except Exception as e:
        st.error(f"❌ Error loading weight data: {e}")
    
    # Weight entry form
    with st.form("weight_form"):
        st.subheader("➕ Add New Weight Entry")
        current_weight = st.session_state.profile.get("weight", 60)
        col1, col2 = st.columns([3, 1])
        with col1:
            new_weight = st.number_input("Current Weight (kg)", 20.0, 300.0, 
                                        value=safe_float(current_weight), label_visibility="collapsed")
        with col2:
            add_weight = st.form_submit_button("➕ Add Entry", use_container_width=True)
    
    if add_weight:
        try:
            # Add weight log
            supabase.table("weight_log").insert({
                "user_id": st.session_state.user["id"],
                "date": datetime.now().strftime("%Y-%m-%d"),
                "weight": new_weight
            }).execute()
            
            # Update current weight in profile
            if st.session_state.profile:
                update_data = {"weight": new_weight}
                if st.session_state.profile.get("id"):
                    supabase.table("profiles").update(update_data).eq("id", st.session_state.profile["id"]).execute()
                else:
                    update_data["user_id"] = st.session_state.user["id"]
                    supabase.table("profiles").insert(update_data).execute()
                
                # Update session state
                st.session_state.profile["weight"] = new_weight
            
            st.success("✅ Weight added! Refresh to see updated chart.")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error saving weight: {e}")

def show_settings():
    """Settings page"""
    st.title("⚙️ Account Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Account Info")
        st.info(f"**Username:** {st.session_state.user['username']}")
        if st.session_state.user.get('email'):
            st.info(f"**Email:** {st.session_state.user['email']}")
        
        st.markdown("---")
        st.subheader("🔑 Change Password")
        
        with st.form("password_form"):
            current = st.text_input("Current Password", type="password")
            new = st.text_input("New Password", type="password")
            confirm = st.text_input("Confirm New Password", type="password")
            change_btn = st.form_submit_button("🔄 Change Password", use_container_width=True)
            
            if change_btn:
                hashed_current = hash_password(current)
                if hashed_current != st.session_state.user['password']:
                    st.error("❌ Current password is incorrect")
                elif new != confirm:
                    st.error("❌ New passwords don't match")
                elif not new:
                    st.error("❌ New password cannot be empty")
                else:
                    hashed_new = hash_password(new)
                    supabase.table("users").update({"password": hashed_new})\
                        .eq("id", st.session_state.user["id"]).execute()
                    st.session_state.user['password'] = hashed_new
                    st.success("✅ Password updated successfully!")
    
    with col2:
        st.subheader("📊 Data Management")
        
        # Display user's workout history
        try:
            workouts = supabase.table("workouts").select("date, plan")\
                .eq("user_id", st.session_state.user["id"])\
                .order("date", desc=True)\
                .limit(5).execute().data
            
            if workouts:
                st.write("**Recent Workouts:**")
                for w in workouts:
                    with st.expander(f"Workout from {w['date']}"):
                        st.write(w['plan'][:200] + "...")
            else:
                st.info("No workouts saved yet.")
        except:
            st.warning("Could not load workout history.")
        
        st.markdown("---")
        
        if st.button("🗑️ Clear All Workout Data", type="secondary", use_container_width=True):
            if st.checkbox("I'm sure I want to delete all my workout history"):
                supabase.table("workouts").delete().eq("user_id", st.session_state.user["id"]).execute()
                st.success("✅ Workout data cleared!")
                st.rerun()

# -------------------- App Router --------------------
def main():
    # Show navbar if logged in
    if st.session_state.logged_in:
        show_navbar()
        show_user_info()
    
    # Route to correct page
    if not st.session_state.logged_in:
        if st.session_state.current_page == "login":
            show_login()
        elif st.session_state.current_page == "signup":
            show_signup()
    else:
        if st.session_state.current_page == "profile":
            show_profile()
        elif st.session_state.current_page == "workout":
            show_workout()
        elif st.session_state.current_page == "meal":
            show_meal()
        elif st.session_state.current_page == "progress":
            show_progress()
        elif st.session_state.current_page == "settings":
            show_settings()

if __name__ == "__main__":
    main()