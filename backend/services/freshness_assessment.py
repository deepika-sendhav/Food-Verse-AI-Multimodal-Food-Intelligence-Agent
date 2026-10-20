import re

from backend.schemas import (
    FreshnessAnalysisResponse,
    FreshnessFeatures,
    FreshnessRuleAssessment,
)
from backend.services.freshness_classifier import FreshnessModelResult

SAFETY_RECOMMENDATIONS = {
    "fresh": {
        "safety_status": "Likely safe",
        "recommendation": "Store properly and consume within the usual time.",
        "color": "green",
        "alert_level": "none",
    },
    "moderately_fresh": {
        "safety_status": "Consume soon",
        "recommendation": "Use today or cook thoroughly; check smell and texture.",
        "color": "amber",
        "alert_level": "warning",
    },
    "spoiled": {
        "safety_status": "Unsafe",
        "recommendation": "Discard it; do not taste it to test.",
        "color": "red",
        "alert_level": "critical",
    },
    "uncertain": {
        "safety_status": "Cannot determine",
        "recommendation": "Retake a clearer photo and check smell, texture, and date.",
        "color": "gray",
        "alert_level": "info",
    },
}
SAFETY_DISCLAIMER = (
    "This is a visual estimate, not a food safety guarantee. When in doubt, throw it out."
)
STRONG_MOLD_FRACTION = 0.01
LEVEL_ORDER = {
    "fresh": 0,
    "moderately_fresh": 1,
    "spoiled": 2,
}


def assess_freshness_rules(features: FreshnessFeatures) -> FreshnessRuleAssessment:
    """Score image-only signals; this heuristic is not a food safety test."""
    signals = []
    score = 100.0

    discoloration_penalty = min(
        35.0,
        features.yellow_brown_fraction * 50
        + features.dark_discoloration_fraction * 30,
    )
    score -= discoloration_penalty
    signals.append(
        f"Yellow/brown discoloration: {features.yellow_brown_fraction:.1%}; "
        f"dark discoloration: {features.dark_discoloration_fraction:.1%}."
    )

    mold_fraction = features.surface_patterns.mold_like_pattern_fraction
    mold_penalty = min(70.0, mold_fraction * 1000)
    score -= mold_penalty
    signals.append(f"Mold-like visual pattern fraction: {mold_fraction:.2%}.")

    texture_penalty = (1 - features.texture.smoothness_score) * 15
    consistency_penalty = (1 - features.color.consistency_score) * 15
    score -= texture_penalty + consistency_penalty
    signals.append(
        f"Texture smoothness: {features.texture.smoothness_score:.2f}; "
        f"color consistency: {features.color.consistency_score:.2f}."
    )

    flags = features.quality_flags
    quality_penalties = (
        (flags.too_dark, 15.0, "image is too dark"),
        (flags.too_bright, 5.0, "image is too bright"),
        (flags.blurry, 10.0, "image is blurry"),
        (flags.low_contrast, 10.0, "image has low contrast"),
    )
    for active, penalty, description in quality_penalties:
        if active:
            score -= penalty
            signals.append(f"Quality limitation: {description}.")

    return FreshnessRuleAssessment(score=max(0.0, min(100.0, score)), signals=signals)


def _level_for_score(score: float) -> str:
    if score >= 70:
        return "fresh"
    if score >= 40:
        return "moderately_fresh"
    return "spoiled"


def _combine_levels(
    rule_level: str,
    model_level: str | None,
    mold_fraction: float,
) -> str:
    if model_level is None:
        return rule_level
    strong_mold = mold_fraction >= STRONG_MOLD_FRACTION
    if model_level == "uncertain":
        return "spoiled" if strong_mold else "uncertain"

    distance = abs(LEVEL_ORDER[rule_level] - LEVEL_ORDER[model_level])
    if distance == 0:
        return rule_level
    if distance == 1:
        # For mixed evidence, select the less-fresh (more cautious) assessment.
        return max((rule_level, model_level), key=LEVEL_ORDER.__getitem__)
    if strong_mold:
        return "spoiled"
    return "uncertain"


def _confidence(
    score: float,
    rule_level: str,
    model_level: str | None,
    features: FreshnessFeatures,
) -> float:
    if model_level is None:
        confidence = 58.0
    elif model_level == "uncertain":
        confidence = 42.0
    else:
        level_distance = abs(LEVEL_ORDER[rule_level] - LEVEL_ORDER[model_level])
        confidence = {0: 82.0, 1: 64.0, 2: 42.0}[level_distance]

    threshold_distance = min(abs(score - 40), abs(score - 70), 30)
    confidence += threshold_distance / 30 * 8
    flags = features.quality_flags
    confidence -= (
        12 * flags.too_dark
        + 5 * flags.too_bright
        + 10 * flags.blurry
        + 8 * flags.low_contrast
    )
    return round(max(0.0, min(90.0, confidence)), 1)


def _storage_warnings(
    item_name: str | None,
    storage_time: str | None,
    storage_type: str | None,
) -> list[str]:
    warnings = []
    storage_text = (storage_type or "").casefold()
    duration_text = (storage_time or "").casefold()
    duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", duration_text)
    minutes = None
    if duration_match:
        amount = float(duration_match.group(1))
        unit = duration_match.group(2)
        minutes = amount * (60 if unit.startswith("h") else 1)
    room_temperature = any(
        term in storage_text
        for term in ("room", "ambient", "counter")
    )
    if minutes is not None and minutes > 120 and room_temperature:
        warnings.append(
            "The reported room-temperature storage exceeds two hours; this can increase risk for perishable food."
        )

    if item_name:
        food_name = item_name.casefold()
        higher_risk_foods = (
            "rice",
            "meat",
            "chicken",
            "beef",
            "pork",
            "fish",
            "seafood",
            "shrimp",
            "prawn",
            "dairy",
            "milk",
            "cheese",
            "yogurt",
            "yoghurt",
            "paneer",
            "curd",
            "butter",
            "cream",
            "ghee",
            "egg",
        )
        if any(re.search(rf"\b{re.escape(term)}\b", food_name) for term in higher_risk_foods):
            warnings.append(
                "This food type can require careful time-temperature control; appearance alone cannot establish safe storage."
            )
    return warnings


def combine_freshness_assessment(
    features: FreshnessFeatures,
    rule_assessment: FreshnessRuleAssessment,
    model_result: FreshnessModelResult | None,
    *,
    storage_time: str | None = None,
    storage_type: str | None = None,
    model_skipped_reason: str | None = None,
) -> FreshnessAnalysisResponse:
    rule_level = _level_for_score(rule_assessment.score)
    model_level = model_result.freshness_level if model_result else None
    final_level = _combine_levels(
        rule_level,
        model_level,
        features.surface_patterns.mold_like_pattern_fraction,
    )
    confidence = _confidence(
        rule_assessment.score,
        rule_level,
        model_level,
        features,
    )
    item_name = model_result.item_name if model_result else None
    detected_signs = model_result.detected_signs if model_result else []
    uncertainties = [
        "Visual analysis cannot confirm food safety; use smell, texture, storage history, and date as well."
    ]
    if model_skipped_reason:
        uncertainties.append(f"Vision assessment was skipped: {model_skipped_reason}")
    if features.quality_flags.too_dark or features.quality_flags.blurry or features.quality_flags.low_contrast:
        uncertainties.append("Image quality limits the reliability of visual freshness assessment.")
    if model_result and model_level != rule_level:
        uncertainties.append(
            f"The vision assessment ({model_level}) differed from the feature-based assessment ({rule_level}); the final result uses a cautious combination."
        )

    if model_result:
        reasoning = (
            f"Vision assessment: {model_result.reasoning} "
            f"Feature-based assessment: {rule_level} (score {rule_assessment.score:.1f}/100)."
        )
    else:
        reasoning = (
            f"Rules-only assessment: score {rule_assessment.score:.1f}/100 maps to {rule_level}. "
            "The vision model was unavailable, so no visual-language assessment was included."
        )
    recommendation = SAFETY_RECOMMENDATIONS[final_level]
    return FreshnessAnalysisResponse(
        success=True,
        item_name=item_name,
        freshness_level=final_level,
        confidence=confidence,
        safety_status=recommendation["safety_status"],
        detected_signs=detected_signs,
        reasoning=reasoning,
        recommendation=recommendation["recommendation"],
        safety_warnings=_storage_warnings(item_name, storage_time, storage_type),
        safety_disclaimer=SAFETY_DISCLAIMER,
        rule_assessment=rule_assessment,
        features=features,
        uncertainties=uncertainties,
        color=recommendation["color"],
        alert_level=recommendation["alert_level"],
    )
