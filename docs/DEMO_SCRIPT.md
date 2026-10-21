# FoodVerse AI live-demo walkthrough (5–7 minutes)

## Before the demo

- Start the backend and frontend using the root README.
- Confirm `/api/health` responds and note whether the UI shows live mode or
  the demo-mode banner.
- For live mode, use synthetic/non-sensitive sample media and ensure the
  backend has a Groq key. Do not use real personal health information.
- Keep one JPG/PNG/WEBP food photo, one produce photo, and a short kitchen
  photo or clip (MP4/MOV/AVI/WEBM, no longer than 120 seconds) ready. There
  are no bundled images or videos.

## Walkthrough

### 1. Dashboard — 30–45 seconds

**Say:** “FoodVerse brings several small kitchen workflows into one place.
This first-visit card suggests the order; the top bar also reports API and
demo status.”

**Do:** Point out the six dashboard cards and the Upload → Analyze →
Understand → Act flow. Leave the demo route card visible.

**Expected:** A responsive dashboard, API health status, module descriptions,
and (when enabled) the persistent “Demo mode: sample data only” banner.

**Fallback:** If health is offline or a later model call is rate-limited, set
`DEMO_MODE=true` in the backend environment and restart the backend. Reload the
page and confirm the banner before presenting sample outputs.

### 2. Food recognition — 45–60 seconds

**Sample input:** Select a clear JPG/PNG/WEBP photo of a plated lentil-and-rice
bowl. Leave serving size empty.

**Say:** “The serving size is optional, and a blank value avoids pretending
the photo gives us a precise weight.”

**Expected:** Dish and ingredient suggestions, estimated nutrition, and
uncertainty/source notes. Null nutrition appears as “Not available.”

**Fallback:** Switch to `DEMO_MODE=true`; submit the same form and explain that
the labeled result is a synthetic sample, not analysis of the photo.

### 3. Freshness detector — 45–60 seconds

**Sample input:** Select a clear photo of a fresh apple or leafy greens. Enter
`refrigerated for 2 days` in storage time and choose Refrigerator.

**Say:** “This is a visual cue, not a food-safety test. It cannot detect
pathogens or toxins.”

**Expected:** A freshness verdict, confidence, visible signs, recommendation,
safety disclaimer, and the collapsible measured-features panel.

**Fallback:** Switch to demo mode and use the sample output. Point out that
visual features and the verdict are explicitly synthetic.

### 4. Hygiene monitor — 60–75 seconds

**Sample input:** Choose a short clip or photo of a clean preparation area.
Set interval to `5` seconds and context to `Review visible handwashing and
surface practices`.

**Say:** “Only visible evidence is reviewed. A limited view should not be
treated as proof of a violation or compliance.”

**Expected:** A progress state, coaching-style result, evidence coverage,
alerts, and skipped/failed frame notes when applicable.

**Fallback:** Switch to demo mode. The sample intentionally has partial
evidence and a simulated frame failure, so demonstrate why the UI does not
overstate confidence.

### 5. Kitchen assistant — 45–60 seconds

**Sample input:** Click **Use sample text**. It fills: “I have cooked lentils,
spinach, lemon, garlic, and brown rice. Suggest a simple beginner-friendly
dinner.” Leave servings at 2 and skill at Beginner.

**Say:** “Dictation, when supported by the browser, puts speech into this text
field. No audio is uploaded.”

**Expected:** An ingredient list, ordered short recipe steps, safety notes,
time estimate, and cook mode.

**Fallback:** Switch to demo mode. The sample recipe is clearly identified as
synthetic and independent of the text entered.

### 6. Meal planner and safety gate — 75–90 seconds

**Sample input:** Click **Fill example profile**, save the made-up adult
vegetarian profile, and choose a daily plan. Then edit the age to `17` and
save again to show the professional-review gate. Do not enter real health data.

**Say:** “The profile is held in backend memory, is not persisted in browser
storage, and personalized plans are withheld when a safety gate applies.”

**Expected:** For the adult profile, a daily plan or labeled demo plan. For the
under-18 profile, a professional-review-required result with no personalized
meal plan.

**Fallback:** Switch to demo mode and repeat. Demo mode selects a dedicated
synthetic safety-gate response for the under-18 sample profile.

## Wrap-up — 20 seconds

Remind viewers that estimates are not medical, dietetic, or food-safety
advice. Profiles expire with the in-memory backend; uploaded media is not
retained by this application. Ask before recording screenshots that could
show user-provided information.
