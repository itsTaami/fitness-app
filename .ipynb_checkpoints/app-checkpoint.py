import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import uuid
import hashlib
import json
from supabase_client import supabase
from groq_api import call_groq
from prompts import build_workout_prompt, build_meal_prompt
from helpers import safe_int, safe_float

st.set_page_config(page_title="Level-Up Fitness", layout="wide")

# -------------------- Constants --------------------
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.2-90b-text-preview",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
    "gemma2-9b-it"
]

MIN_AGE = 10
MAX_AGE = 120

# Common exercises for autocomplete
COMMON_EXERCISES = [
    "Pull-ups", "Push-ups", "Squats", "Lunges", "Bench Press", 
    "Deadlifts", "Bicep Curls", "Tricep Dips", "Plank", "Burpees",
    "Mountain Climbers", "Jumping Jacks", "Leg Press", "Shoulder Press",
    "Lat Pulldown", "Crunches", "Russian Twists", "Leg Raises",
    "Dumbbell Rows", "Calf Raises", "Bench Dips", "Kettlebell Swings"
]

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

# -------------------- Workout Log Functions --------------------
def get_workout_logs(user_id, selected_date=None):
    """Get workout logs for a user"""
    try:
        query = supabase.table("workout_logs").select("*").eq("user_id", user_id)
        
        if selected_date:
            query = query.eq("date", selected_date.strftime("%Y-%m-%d"))
        
        result = query.order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"Error loading workout logs: {e}")
        return []

def save_workout_log(user_id, exercise_data):
    """Save a workout log"""
    try:
        result = supabase.table("workout_logs").insert({
            "user_id": user_id,
            "date": exercise_data["date"].strftime("%Y-%m-%d"),
            "exercise": exercise_data["exercise"],
            "sets": exercise_data["sets"],
            "reps": exercise_data["reps"],
            "weight": exercise_data.get("weight"),
            "notes": exercise_data.get("notes", ""),
            "completed": exercise_data.get("completed", False)
        }).execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Error saving workout log: {e}")
        return None

def update_workout_log(log_id, updates):
    """Update a workout log"""
    try:
        result = supabase.table("workout_logs").update(updates).eq("id", log_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Error updating workout log: {e}")
        return None

def delete_workout_log(log_id):
    """Delete a workout log"""
    try:
        supabase.table("workout_logs").delete().eq("id", log_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting workout log: {e}")
        return False

def get_workout_summary(user_id, days=7):
    """Get workout summary for last N days"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        result = supabase.table("workout_logs")\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("date", start_date)\
            .execute()
        
        return result.data
    except Exception as e:
        st.error(f"Error loading workout summary: {e}")
        return []

# -------------------- Initialize Session State --------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'profile' not in st.session_state:
    st.session_state.profile = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = date.today()

# -------------------- Navbar Component --------------------
def show_navbar():
    """Display top navigation bar with all options"""
    # Create 8 columns for better spacing
    cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1])
    
    with cols[0]:
        st.markdown("## 🏋️ Level-Up Fitness")
    
    # Navigation buttons - now using all columns
    if st.session_state.logged_in:
        with cols[1]:
            if st.button("🏠 Profile", use_container_width=True, key="nav_profile"):
                st.session_state.current_page = "profile"
                st.rerun()
        
        with cols[2]:
            if st.button("📝 Log", use_container_width=True, key="nav_workout_log"):
                st.session_state.current_page = "workout_log"
                st.rerun()
        
        with cols[3]:
            if st.button("💪 AI", use_container_width=True, key="nav_ai_workout"):
                st.session_state.current_page = "ai_workout"
                st.rerun()
        
        with cols[4]:
            if st.button("🍎 Meal", use_container_width=True, key="nav_ai_meal"):
                st.session_state.current_page = "ai_meal"
                st.rerun()
        
        with cols[5]:
            if st.button("📈 Stats", use_container_width=True, key="nav_progress"):
                st.session_state.current_page = "progress"
                st.rerun()
        
        with cols[6]:
            if st.button("⚙️ Settings", use_container_width=True, key="nav_settings", 
                        help="Settings"):
                st.session_state.current_page = "settings"
                st.rerun()
        
        with cols[7]:
            if st.button("🚪Гарах", use_container_width=True, key="nav_logout",
                        help="Logout", type="secondary"):
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
        with st.expander(f" {st.session_state.user['username']}'s Stats", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Weight", f"{st.session_state.profile.get('weight', 0)} kg")
            with col2:
                st.metric("Target Weight", f"{st.session_state.profile.get('target_weight', 0)} kg")
            with col3:
                if st.session_state.profile.get('height'):
                    st.metric("Height", f"{st.session_state.profile.get('height')} cm")
            with col4:
                # Get today's workout count
                today_logs = get_workout_logs(st.session_state.user["id"], st.session_state.selected_date)
                completed = sum(1 for log in today_logs if log.get("completed", False))
                total = len(today_logs)
                st.metric("Today's Workout", f"{completed}/{total}")

# -------------------- Authentication Pages --------------------
def show_login():
    """Login page"""
    st.title(" Login ")
    
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
    st.title(" Create Account")
    
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

# -------------------- Workout Log/To-Do List Page --------------------
def show_workout_log():
    """Workout log/to-do list page"""
    st.title(" Workout Tracker")
    
    if not st.session_state.profile:
        st.warning(" Please fill out your profile first!")
        return
    
    # Date selector
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selected_date = st.date_input(
            "Select Date",
            value=st.session_state.selected_date,
            key="date_selector"
        )
        st.session_state.selected_date = selected_date
    
    st.markdown("---")
    
    # Two columns: Add new exercise and list of exercises
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(" Add Exercise")
        with st.form("add_exercise_form"):
            # Exercise selection with autocomplete
            exercise = st.selectbox(
                "Exercise",
                options=[""] + sorted(COMMON_EXERCISES),
                format_func=lambda x: "Select exercise..." if x == "" else x
            )
            
            # Custom exercise input
            custom_exercise = st.text_input("Or enter custom exercise")
            
            # Use custom exercise if provided
            if custom_exercise:
                exercise = custom_exercise
            
            col_sets, col_reps = st.columns(2)
            with col_sets:
                sets = st.number_input("Sets", min_value=1, max_value=20, value=3)
            with col_reps:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
            
            weight = st.number_input("Weight (kg) - optional", min_value=0.0, value=0.0)
            notes = st.text_area("Notes - optional", placeholder="e.g., Difficult, Easy, Need improvement")
            
            add_btn = st.form_submit_button("Add to Workout Log", use_container_width=True)
            
            if add_btn and exercise:
                exercise_data = {
                    "date": selected_date,
                    "exercise": exercise,
                    "sets": int(sets),
                    "reps": int(reps),
                    "weight": float(weight) if weight > 0 else None,
                    "notes": notes,
                    "completed": False
                }
                
                saved = save_workout_log(st.session_state.user["id"], exercise_data)
                if saved:
                    st.success(f" Added {sets}x{reps} {exercise} to your workout!")
                    st.rerun()
                else:
                    st.error(" Failed to save exercise")
    
    with col2:
        st.subheader(f" Today's Workout ({selected_date})")
        
        # Get today's workout logs
        workout_logs = get_workout_logs(st.session_state.user["id"], selected_date)
        
        if not workout_logs:
            st.info("No exercises logged for today. Add your first exercise!")
        else:
            # Calculate totals
            total_exercises = len(workout_logs)
            completed_exercises = sum(1 for log in workout_logs if log.get("completed", False))
            
            # Progress bar
            if total_exercises > 0:
                progress = completed_exercises / total_exercises
                st.progress(progress, text=f"Completed: {completed_exercises}/{total_exercises} exercises")
            
            # Display each exercise
            for i, log in enumerate(workout_logs):
                with st.container():
                    col1, col2, col3 = st.columns([4, 2, 1])
                    
                    with col1:
                        # Display exercise info
                        weight_text = f" @ {log['weight']}kg" if log.get('weight') else ""
                        notes_text = f" - {log['notes']}" if log.get('notes') else ""
                        
                        if log.get('completed', False):
                            st.markdown(f" **{log['exercise']}**: {log['sets']}x{log['reps']}{weight_text}{notes_text}")
                        else:
                            st.markdown(f" **{log['exercise']}**: {log['sets']}x{log['reps']}{weight_text}{notes_text}")
                    
                    with col2:
                        # Toggle completion
                        current_status = log.get('completed', False)
                        new_status = st.checkbox(
                            "Completed", 
                            value=current_status, 
                            key=f"complete_{log['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if new_status != current_status:
                            update_workout_log(log['id'], {"completed": new_status})
                            st.rerun()
                    
                    with col3:
                        # Delete button
                        if st.button("🗑️", key=f"delete_{log['id']}"):
                            delete_workout_log(log['id'])
                            st.success("Exercise deleted!")
                            st.rerun()
                    
                    st.markdown("---")
    
    # Weekly summary
    st.markdown("---")
    st.subheader("Weekly Summary")
    
    weekly_logs = get_workout_summary(st.session_state.user["id"], days=7)
    
    if weekly_logs:
        # Create DataFrame for visualization
        df = pd.DataFrame(weekly_logs)
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by date
        daily_summary = df.groupby('date').agg({
            'exercise': 'count',
            'completed': 'sum'
        }).rename(columns={'exercise': 'total_exercises'})
        
        # Plot
        st.bar_chart(daily_summary[['total_exercises', 'completed']])
        
        # Most common exercises
        st.write("**Most Common Exercises This Week:**")
        top_exercises = df['exercise'].value_counts().head(5)
        for exercise, count in top_exercises.items():
            st.write(f"- {exercise}: {count} times")
    else:
        st.info("No workout data for this week yet.")

# -------------------- AI Workout Generator Page --------------------
def show_ai_workout():
    """AI Workout generator page"""
    st.title(" Workout Generator")
    
    if not st.session_state.profile or not st.session_state.profile.get("name"):
        st.warning("Please fill out your profile first!")
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
                generate = st.form_submit_button(" Generate Workout", use_container_width=True)
        
        with col2:
            if st.session_state.profile:
                st.info("### Your Profile")
                st.write(f"**Name:** {st.session_state.profile.get('name', 'Not set')}")
                st.write(f"**Age:** {st.session_state.profile.get('age', 'Not set')}")
                st.write(f"**Weight:** {st.session_state.profile.get('weight', 'Not set')} kg")
                st.write(f"**Height:** {st.session_state.profile.get('height', 'Not set')} cm")
    
    if generate:
        with st.spinner("Generating your personalized workout plan..."):
            try:
                prompt = build_workout_prompt(
                    st.session_state.profile, goal, duration, level, 
                    focus, equipment, days, notes
                )
                result = call_groq(prompt)
                
                if result.startswith("❌"):
                    st.er
                    ror(result)
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
                    
                    # Parse AI workout and suggest adding to workout log
                    st.info(" **Quick Add to Workout Log**")
                    st.write("Want to add these exercises to your workout log?")
                    
                    # Simple parser to extract exercises (this is basic - you can enhance it)
                    lines = result.split('\n')
                    for line in lines:
                        if 'x' in line and ('reps' in line.lower() or '×' in line):
                            parts = line.split()
                            for part in parts:
                                if 'x' in part or '×' in part:
                                    try:
                                        sets_reps = part.replace('×', 'x')
                                        exercise = ' '.join(parts[parts.index(part)+1:])[:30]
                                        if exercise and len(exercise) > 2:
                                            col1, col2 = st.columns([3, 1])
                                            with col1:
                                                st.write(f"{sets_reps} {exercise}")
                                            with col2:
                                                if st.button("➕ Add", key=f"add_{hash(exercise)}"):
                                                    # Parse sets and reps
                                                    if 'x' in sets_reps:
                                                        s, r = sets_reps.split('x')[:2]
                                                        exercise_data = {
                                                            "date": date.today(),
                                                            "exercise": exercise,
                                                            "sets": int(s),
                                                            "reps": int(r),
                                                            "completed": False
                                                        }
                                                        save_workout_log(st.session_state.user["id"], exercise_data)
                                                        st.success(f"Added {exercise}!")
                                                        st.rerun()
                                    except:
                                        continue
                    
            except Exception as e:
                st.error(f"Error generating workout: {e}")

# -------------------- Other Pages (Profile, AI Meal, Progress, Settings) --------------------
# [Keep the existing show_profile(), show_ai_meal(), show_progress(), show_settings() functions]
# They remain the same as in the previous version

def show_profile():
    """Profile page"""
    st.title(" Profile Settings")
    
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
        
        submit_profile = st.form_submit_button(" Save Profile", use_container_width=True)
    
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
            st.success(" Profile saved successfully!")
        else:
            st.error(" Failed to save profile")

def show_ai_meal():
    """AI Meal Plan Generator page"""
    st.title("Meal Plan Generator")
    
    if not st.session_state.profile or not st.session_state.profile.get("name"):
        st.warning("Please fill out your profile first!")
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
                generate_meal = st.form_submit_button("Generate Meal Plan", use_container_width=True)
        
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
            
        with st.spinner("Generating your personalized meal plan..."):
            try:
                prompt = build_meal_prompt(
                    st.session_state.profile, goal, diet_type, meals_per_day, 
                    cuisine, restrictions, notes
                )
                result = call_groq(prompt)
                
                if result.startswith("❌"):
                    st.error(result)
                else:
                    st.success(" Meal Plan Generated!")
                    st.markdown("---")
                    st.markdown(result)
                    
                    # Save to database
                    supabase.table("meals").insert({
                        "user_id": st.session_state.user["id"],
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "plan": result
                    }).execute()
                    
            except Exception as e:
                st.error(f" Error generating meal plan: {e}")

def show_progress():
    """Progress tracking page"""
    st.title("Progress Dashboard")
    
    if not st.session_state.profile:
        st.warning(" Please save your profile first!")
        return
    
    # Tabs for different progress metrics
    tab1, tab2, tab3 = st.tabs(["Weight", "Workouts", "Summary"])
    
    with tab1:
        # Weight tracking (existing)
        try:
            weight_logs = supabase.table("weight_log")\
                .select("*")\
                .eq("user_id", st.session_state.user["id"])\
                .order("date", desc=True)\
                .execute().data
            
            if weight_logs:
                df = pd.DataFrame(weight_logs)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                
                st.subheader("Weight Trend")
                st.line_chart(df.set_index("date")["weight"])
                
                st.subheader("Recent Entries")
                display_df = df[["date", "weight"]].copy()
                display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
                display_df = display_df.sort_values("date", ascending=False)
                st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)
            else:
                st.info(" No weight data yet.")
                
        except Exception as e:
            st.error(f" Error loading weight data: {e}")
        
        # Weight entry form
        with st.form("weight_form"):
            st.subheader(" Add New Weight Entry")
            current_weight = st.session_state.profile.get("weight", 60)
            col1, col2 = st.columns([3, 1])
            with col1:
                new_weight = st.number_input("Current Weight (kg)", 20.0, 300.0, 
                                            value=safe_float(current_weight), label_visibility="collapsed")
            with col2:
                add_weight = st.form_submit_button(" Add Entry", use_container_width=True)
        
        if add_weight:
            try:
                supabase.table("weight_log").insert({
                    "user_id": st.session_state.user["id"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "weight": new_weight
                }).execute()
                
                if st.session_state.profile:
                    update_data = {"weight": new_weight}
                    if st.session_state.profile.get("id"):
                        supabase.table("profiles").update(update_data).eq("id", st.session_state.profile["id"]).execute()
                    else:
                        update_data["user_id"] = st.session_state.user["id"]
                        supabase.table("profiles").insert(update_data).execute()
                    
                    st.session_state.profile["weight"] = new_weight
                
                st.success(" Weight added!")
                st.rerun()
                
            except Exception as e:
                st.error(f" Error saving weight: {e}")
    
    with tab2:
        # Workout progress
        st.subheader("Workout Statistics")
        
        try:
            workout_logs = get_workout_summary(st.session_state.user["id"], days=30)
            
            if workout_logs:
                df = pd.DataFrame(workout_logs)
                df['date'] = pd.to_datetime(df['date'])
                
                # Monthly summary
                st.metric("Total Exercises (30 days)", len(df))
                st.metric("Completed Exercises", df['completed'].sum())
                
                # Daily exercise count
                daily_counts = df.groupby('date').size().reset_index(name='count')
                st.subheader("Exercises per Day")
                st.line_chart(daily_counts.set_index('date')['count'])
                
                # Most frequent exercises
                st.subheader("Top Exercises")
                top_exercises = df['exercise'].value_counts().head(10)
                st.bar_chart(top_exercises)
            else:
                st.info("No workout data for the last 30 days.")
                
        except Exception as e:
            st.error(f"Error loading workout stats: {e}")
    
    with tab3:
        # Overall summary
        st.subheader("Fitness Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Weight progress
            if st.session_state.profile.get('weight') and st.session_state.profile.get('target_weight'):
                current = st.session_state.profile['weight']
                target = st.session_state.profile['target_weight']
                difference = target - current
                st.metric("Weight Progress", f"{current} kg", f"{difference:+.1f} kg to target")
        
        with col2:
            # Workout consistency
            workout_logs = get_workout_summary(st.session_state.user["id"], days=7)
            days_with_workouts = len(set(log['date'] for log in workout_logs))
            st.metric("Workout Days (7 days)", days_with_workouts, "days")
        
        with col3:
            # Completion rate
            if workout_logs:
                completion_rate = (sum(log.get('completed', False) for log in workout_logs) / len(workout_logs)) * 100
                st.metric("Completion Rate", f"{completion_rate:.1f}%")

def show_settings():
    """Settings page"""
    st.title("Account Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(" Account Info")
        st.info(f"**Username:** {st.session_state.user['username']}")
        if st.session_state.user.get('email'):
            st.info(f"**Email:** {st.session_state.user['email']}")
        
        st.markdown("---")
        st.subheader(" Change Password")
        
        with st.form("password_form"):
            current = st.text_input("Current Password", type="password")
            new = st.text_input("New Password", type="password")
            confirm = st.text_input("Confirm New Password", type="password")
            change_btn = st.form_submit_button("Change Password", use_container_width=True)
            
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
        st.subheader("Data Management")
        
        # Display workout history
        try:
            workouts = supabase.table("workouts").select("date, plan")\
                .eq("user_id", st.session_state.user["id"])\
                .order("date", desc=True)\
                .limit(5).execute().data
            
            if workouts:
                st.write("**Recent AI Workouts:**")
                for w in workouts:
                    with st.expander(f"Workout from {w['date']}"):
                        st.write(w['plan'][:200] + "...")
            else:
                st.info("No AI workouts saved yet.")
        except:
            st.warning("Could not load workout history.")
        
        st.markdown("---")
        
        if st.button("🗑️ Clear All Workout Data", type="secondary", use_container_width=True):
            if st.checkbox("I'm sure I want to delete all my workout history"):
                supabase.table("workouts").delete().eq("user_id", st.session_state.user["id"]).execute()
                supabase.table("workout_logs").delete().eq("user_id", st.session_state.user["id"]).execute()
                st.success("✅ All workout data cleared!")
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
        elif st.session_state.current_page == "workout_log":
            show_workout_log()
        elif st.session_state.current_page == "ai_workout":
            show_ai_workout()
        elif st.session_state.current_page == "ai_meal":
            show_ai_meal()
        elif st.session_state.current_page == "progress":
            show_progress()
        elif st.session_state.current_page == "settings":
            show_settings()

if __name__ == "__main__":
    main()