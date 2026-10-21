from backend.schemas import NutritionTargets, UserProfile

ACTIVITY_FACTORS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
GOAL_ADJUSTMENTS: dict[str, float] = {
    "maintain": 0.0,
    "eat_healthier": 0.0,
    "lose_weight": -0.10,
    "gain_weight": 0.10,
    "build_muscle": 0.05,
}
MAX_CALORIE_DEFICIT = 0.15
MINIMUM_DAILY_CALORIES: dict[str, int] = {
    "female": 1200,
    "male": 1500,
    "other": 1200,
    "prefer_not_to_say": 1200,
}
MACRO_SPLITS: dict[str, tuple[float, float, float]] = {
    "maintain": (0.50, 0.20, 0.30),
    "lose_weight": (0.40, 0.30, 0.30),
    "gain_weight": (0.50, 0.20, 0.30),
    "build_muscle": (0.45, 0.30, 0.25),
    "eat_healthier": (0.50, 0.20, 0.30),
}
FIBER_GRAMS_PER_1000_KCAL = 14
HYDRATION_ML_PER_KG = 30


def _bmr(profile: UserProfile) -> tuple[float, bool]:
    base = (
        10 * profile.weight_kg
        + 6.25 * profile.height_cm
        - 5 * profile.age_years
    )
    if profile.sex == "male":
        return base + 5, False
    if profile.sex == "female":
        return base - 161, False
    return (base + 5 + base - 161) / 2, True


def compute_nutrition_targets(profile: UserProfile) -> NutritionTargets:
    bmr, averaged_sex_formula = _bmr(profile)
    tdee = bmr * ACTIVITY_FACTORS[profile.activity_level]
    adjustment = GOAL_ADJUSTMENTS[profile.health_goal]
    notes = [
        "Targets are rounded estimates, not medical prescriptions.",
        "Hydration is general guidance (about 30 ml per kg, rounded); needs vary with climate, activity, and health.",
    ]
    if averaged_sex_formula:
        notes.append(
            "For sex 'other' or 'prefer_not_to_say', BMR uses the average of the male and female Mifflin-St Jeor results."
        )

    if adjustment < -MAX_CALORIE_DEFICIT:
        adjustment = -MAX_CALORIE_DEFICIT
        notes.append("The calorie deficit was capped at 15 percent.")
    calories = tdee * (1 + adjustment)
    if calories < MINIMUM_DAILY_CALORIES[profile.sex]:
        calories = float(MINIMUM_DAILY_CALORIES[profile.sex])
        notes.append(
            f"Calories were raised to the minimum daily estimate of {MINIMUM_DAILY_CALORIES[profile.sex]} kcal."
        )
    calories = round(calories)

    carb_share, protein_share, fat_share = MACRO_SPLITS[profile.health_goal]
    return NutritionTargets(
        calories=calories,
        carbs_g=round(calories * carb_share / 4, 1),
        protein_g=round(calories * protein_share / 4, 1),
        fats_g=round(calories * fat_share / 9, 1),
        fiber_g=round(calories / 1000 * FIBER_GRAMS_PER_1000_KCAL, 1),
        hydration_ml=round(profile.weight_kg * HYDRATION_ML_PER_KG / 50) * 50,
        notes=notes,
    )
