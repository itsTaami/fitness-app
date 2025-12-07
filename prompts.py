def build_workout_prompt(profile, goal, duration, level, focus, equipment, days, notes):
    return f"""
Create a safe teen-friendly workout plan.

### USER
Name: {profile['name']}
Age: {profile['age']}
Gender: {profile['gender']}
Height: {profile['height']} cm
Weight: {profile['weight']} kg

### REQUEST
Goal: {goal}
Duration: {duration}
Experience: {level}
Focus: {focus}
Equipment: {', '.join(equipment)}
Days per week: {days}
Notes: {notes}

### FORMAT
- Short overview
- Warm-up (5–10 min)
- Main workout (sets/reps)
- Weekly plan
- Safe progression advice
- Cooldown
"""

def build_meal_prompt(profile, goal, diet_type, meals_per_day, cuisine, restrictions, notes):
    return f"""
Create a balanced, safe meal plan (no strict calories).

### USER
Name: {profile['name']}
Age: {profile['age']}
Height: {profile['height']} cm
Weight: {profile['weight']} kg

### REQUEST
Goal: {goal}
Diet type: {diet_type}
Meals/day: {meals_per_day}
Cuisine: {cuisine}
Restrictions: {', '.join(restrictions)}
Notes: {notes}

### FORMAT
- Calorie *range*
- Daily meal schedule
- Simple recipes
- 7-day shopping list
"""
