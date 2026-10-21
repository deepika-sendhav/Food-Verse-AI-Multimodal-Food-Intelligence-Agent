import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '../hooks/useTheme.jsx'

const mocks = vi.hoisted(() => ({
  getProfileOptions: vi.fn(),
  getApiHealth: vi.fn(),
  requestMealPlan: vi.fn(),
  createProfile: vi.fn(),
  deleteProfile: vi.fn(),
}))

vi.mock('../api/profile.js', () => ({
  getProfileOptions: mocks.getProfileOptions,
  createProfile: mocks.createProfile,
  deleteProfile: mocks.deleteProfile,
}))
vi.mock('../api/health.js', () => ({
  getApiHealth: mocks.getApiHealth,
}))
vi.mock('../api/mealPlanner.js', () => ({
  generateMealPlan: mocks.requestMealPlan,
}))

import FoodResult from '../components/FoodRecognitionResult.jsx'
import HygieneResult from '../components/HygieneResult.jsx'
import MealPlanner from '../pages/MealPlanner.jsx'
import App from '../App.jsx'
import { validateUpload } from '../utils/validation.js'

const options = {
  sexes: ['female', 'male', 'other', 'prefer_not_to_say'],
  activity_levels: ['sedentary', 'light', 'moderate', 'active', 'very_active'],
  health_goals: [
    'maintain',
    'lose_weight',
    'gain_weight',
    'build_muscle',
    'eat_healthier',
  ],
  diet_types: ['omnivore', 'vegetarian'],
  canonical_allergens: ['milk', 'egg', 'peanut'],
  height_units: ['cm', 'in'],
  weight_units: ['kg', 'lb'],
}

beforeEach(() => {
  window.matchMedia =
    window.matchMedia ||
    (() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() }))
  mocks.getProfileOptions.mockResolvedValue(options)
  mocks.getApiHealth.mockResolvedValue({ status: 'ok', demo: false })
  sessionStorage.clear()
  localStorage.clear()
})
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

const wrap = (element) => render(<ThemeProvider>{element}</ThemeProvider>)

describe('analysis result rendering', () => {
  it('renders null food nutrition as Not available, never as zero', () => {
    wrap(
      <FoodResult
        result={{
          dish_name: 'Soup',
          detected_items: ['lentils'],
          description: 'Warm lentil soup.',
          health_score: null,
          health_label: null,
          reasoning: 'A balanced meal.',
          nutrition: {
            serving_description: 'One serving',
            serving_size_is_assumed: true,
            source: 'Estimate',
            calories_kcal: null,
            protein_g: null,
            carbs_g: 0,
            fats_g: null,
            fiber_g: null,
            sugar_g: null,
            uncertainties: [],
          },
          insights: [],
          alternatives: [],
          uncertainties: [],
        }}
      />,
    )
    expect(screen.getAllByText('Not available').length).toBeGreaterThan(0)
    expect(screen.getByText(/Health score unavailable/)).toBeInTheDocument()
  })

  it('shows insufficient evidence when the hygiene score is null', () => {
    wrap(
      <HygieneResult
        result={{
          summary: 'More evidence is needed.',
          status: 'insufficient_evidence',
          overall_score: null,
          frames_analyzed: 0,
          frames_skipped: [],
          frames_failed: [],
          category_scores: {
            protective_equipment: null,
            food_handling: null,
            cleanliness: null,
          },
          evidence_coverage: 0,
          category_evidence_coverage: {
            protective_equipment: 0,
            food_handling: 0,
            cleanliness: 0,
          },
          violations: [],
          alerts: [],
          disclaimers: [],
        }}
      />,
    )
    expect(screen.getByText('Insufficient evidence')).toBeInTheDocument()
  })
})

describe('MealPlanner safety states', () => {
  it('shows professional review-required state and acknowledgement action', async () => {
    sessionStorage.setItem('foodverse-profile-id', 'profile-123')
    mocks.requestMealPlan.mockResolvedValue({
      success: true,
      status: 'professional_review_required',
      plan_type: 'daily',
      alert_level: 'warning',
      targets: {
        calories: null,
        protein_g: null,
        carbs_g: null,
        fats_g: null,
        fiber_g: null,
        hydration_ml: null,
        notes: [],
      },
      days: [],
      weekly_report: null,
      general_outline: [],
      adaptive_suggestions: [],
      warnings: [],
      failed_days: [],
      safety_flags: [{ message: 'Please consult a professional.' }],
      disclaimers: [],
    })
    wrap(<MealPlanner />)
    await screen.findByRole('heading', { level: 2, name: 'Set your table.' })
    fireEvent.click(screen.getByRole('button', { name: 'Generate meal plan' }))
    expect(
      await screen.findByText('A note before you continue'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: 'Show general healthy eating outline',
      }),
    ).toBeInTheDocument()
  })

  it('explains expired profile after a 404', async () => {
    sessionStorage.setItem('foodverse-profile-id', 'expired-id')
    mocks.requestMealPlan.mockRejectedValue(
      Object.assign(new Error('Not found'), { status: 404 }),
    )
    wrap(<MealPlanner />)
    await screen.findByRole('heading', { level: 2, name: 'Set your table.' })
    fireEvent.click(screen.getByRole('button', { name: 'Generate meal plan' }))
    expect(
      await screen.findByText(/Profiles are kept in backend memory and expire/),
    ).toBeInTheDocument()
  })
})

describe('routing and upload validation', () => {
  it('dismisses the first-visit demo tour and remembers the choice', async () => {
    window.history.pushState({}, '', '/')
    const firstRender = wrap(<App />)
    fireEvent.click(
      await screen.findByRole('button', { name: 'Dismiss demo tour' }),
    )
    expect(screen.queryByText('Your suggested demo route')).toBeNull()
    expect(localStorage.getItem('foodverse-demo-tour-dismissed')).toBe('true')
    firstRender.unmount()
    wrap(<App />)
    expect(screen.queryByText('Your suggested demo route')).toBeNull()
  })

  it('shows the persistent demo banner when health reports demo mode', async () => {
    mocks.getApiHealth.mockResolvedValue({
      status: 'ok',
      demo: true,
      demo_warning: 'sample data',
    })
    window.history.pushState({}, '', '/')
    wrap(<App />)
    expect(
      await screen.findByRole('status', {
        name: /Demo mode: sample data only/,
      }),
    ).toBeInTheDocument()
  })

  it.each([
    ['/', 'Food,'],
    ['/food-recognition', 'Food recognition'],
    ['/freshness-detector', 'Freshness detector'],
    ['/hygiene-monitor', 'Hygiene monitor'],
    ['/kitchen-assistant', 'Kitchen assistant'],
    ['/meal-planner', 'Meal planner'],
  ])('renders route %s', async (path, heading) => {
    window.history.pushState({}, '', path)
    wrap(<App />)
    expect(
      await screen.findByRole('heading', {
        level: 1,
        name: new RegExp(heading),
      }),
    ).toBeInTheDocument()
  })

  it('redirects unknown paths to the dashboard', async () => {
    window.history.pushState({}, '', '/not-a-module')
    wrap(<App />)
    expect(
      await screen.findByRole('heading', {
        level: 2,
        name: 'Good decisions start here.',
      }),
    ).toBeInTheDocument()
  })

  it('rejects an invalid type and an oversized image', () => {
    expect(
      validateUpload(new File(['text'], 'notes.txt', { type: 'text/plain' })),
    ).toMatch(/Choose a JPG/)
    expect(
      validateUpload(
        new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'large.png', {
          type: 'image/png',
        }),
      ),
    ).toMatch(/File too large/)
  })
})
