import {
  ArrowDown,
  ArrowRight,
  ChefHat,
  ClipboardList,
  Leaf,
  ScanSearch,
  ShieldCheck,
  UserRound,
  Upload,
  Sparkles,
  Lightbulb,
  Check,
  X,
} from 'lucide-react'
import { Link, useOutletContext } from 'react-router-dom'
import { useState } from 'react'
import styles from './Dashboard.module.css'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'

const modules = [
  {
    title: 'Food recognition',
    path: '/food-recognition',
    icon: ScanSearch,
    description: 'Identify what is on your plate and explore its nutrition.',
    input: 'A JPG, PNG or WEBP food photo',
    tone: 'green',
  },
  {
    title: 'Freshness detector',
    path: '/freshness-detector',
    icon: Leaf,
    description: 'Look for visual cues that help assess produce freshness.',
    input: 'A produce photo and optional storage notes',
    tone: 'amber',
  },
  {
    title: 'Hygiene monitor',
    path: '/hygiene-monitor',
    icon: ShieldCheck,
    description: 'Review kitchen media for visible food-safety practices.',
    input: 'A kitchen photo or video',
    tone: 'red',
  },
  {
    title: 'Kitchen assistant',
    path: '/kitchen-assistant',
    icon: ChefHat,
    description: 'Turn ingredients or a food photo into a practical recipe.',
    input: 'Ingredients in text, an image, or both',
    tone: 'green',
  },
  {
    title: 'Your food profile',
    path: '/meal-planner#profile',
    icon: UserRound,
    description: 'Set dietary preferences to personalize meal suggestions.',
    input: 'Your goals, diet, allergies and preferences',
    tone: 'green',
  },
  {
    title: 'Meal planner',
    path: '/meal-planner',
    icon: ClipboardList,
    description: 'Build a daily or weekly meal plan around your profile.',
    input: 'Your profile and planning preferences',
    tone: 'amber',
  },
]

export default function Dashboard() {
  const health = useOutletContext()
  const status = health.status
  const [tourVisible, setTourVisible] = useState(
    () => localStorage.getItem('foodverse-demo-tour-dismissed') !== 'true',
  )
  const dismissTour = () => {
    localStorage.setItem('foodverse-demo-tour-dismissed', 'true')
    setTourVisible(false)
  }
  return (
    <div className={`dashboard page-wrap ${styles.editorial}`}>
      <section className="hero">
        <div className="hero__copy">
          <p className="eyebrow">A little more insight, every day</p>
          <h1>
            Food, <em>understood.</em>
          </h1>
          <p>
            Meet your thoughtful kitchen companion. From what’s on your plate to
            what’s in your fridge, make each food decision with more confidence.
          </p>
          <Link className="button button--primary" to="/food-recognition">
            Explore your plate <ArrowRight size={17} />
          </Link>
        </div>
        <div className="hero__art" aria-hidden="true">
          <div className="hero__sun" />
          <div className="hero__leaf hero__leaf--one" />
          <div className="hero__leaf hero__leaf--two" />
          <div className="hero__dish">
            <div className="hero__dish-food">✦</div>
          </div>
          <span className="hero__caption">Good food. Clear thinking.</span>
        </div>
      </section>
      <section
        className={`health-strip health-strip--${status}`}
        aria-live="polite"
      >
        <span className="health-strip__dot" />
        <strong>
          {status === 'online'
            ? 'Your kitchen intelligence is ready.'
            : status === 'checking'
              ? 'Checking your kitchen connection…'
              : 'The backend is not responding right now.'}
        </strong>
        <span>
          {status === 'offline'
            ? 'Start the FoodVerse API to enable analysis.'
            : 'Connection checked every 30 seconds.'}
        </span>
      </section>
      {tourVisible && (
        <Card className="demo-tour">
          <div className="section-title">
            <div>
              <p className="eyebrow">First visit · 5–7 minutes</p>
              <h2>Your suggested demo route</h2>
            </div>
            <Button
              variant="quiet"
              onClick={dismissTour}
              aria-label="Dismiss demo tour"
            >
              <X size={17} />
            </Button>
          </div>
          <ol>
            {modules.map((module) => (
              <li key={module.path}>
                <Link to={module.path}>{module.title}</Link>
              </li>
            ))}
          </ol>
          <p className="muted">
            Start with the dashboard, then visit food recognition, freshness,
            hygiene, the kitchen assistant, and the meal planner.
          </p>
        </Card>
      )}
      <section className="section-block">
        <div className="section-title">
          <div>
            <p className="eyebrow">Explore the toolkit</p>
            <h2>Good decisions start here.</h2>
          </div>
          <span>Six ways to bring clarity to your kitchen</span>
        </div>
        <div className="module-grid">
          {modules.map(
            ({ title, path, icon: Icon, description, input, tone }, index) => (
              <Card key={title} className="module-card">
                <div className="module-card__top">
                  <span className={`module-icon module-icon--${tone}`}>
                    <Icon size={21} />
                  </span>
                  <span className="module-card__number">0{index + 1}</span>
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                <div className="module-card__input">
                  <span>TAKES</span>
                  {input}
                </div>
                <Link className="text-link" to={path}>
                  Open <ArrowRight size={16} />
                </Link>
              </Card>
            ),
          )}
        </div>
      </section>
      <section className="section-block how-it-works">
        <div className="section-title">
          <div>
            <p className="eyebrow">Simple by design</p>
            <h2>Four steps. Better context.</h2>
          </div>
          <Sparkles size={23} />
        </div>
        <div className="steps">
          {[
            {
              title: 'Upload',
              text: 'Share a photo, clip or a few words.',
              icon: Upload,
            },
            {
              title: 'Analyze',
              text: 'AI looks for useful food signals.',
              icon: ScanSearch,
            },
            {
              title: 'Understand',
              text: 'Explore results with clear context.',
              icon: Lightbulb,
            },
            {
              title: 'Act',
              text: 'Choose your next step with care.',
              icon: Check,
            },
          ].map(({ title, text, icon: Icon }, index) => (
            <div className="step" key={title}>
              <span className="step__icon">
                <Icon size={19} />
              </span>
              <span className="step__number">
                {String(index + 1).padStart(2, '0')} <ArrowDown size={12} />
              </span>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
        <p className="disclaimer">
          AI results are estimates and are not a substitute for professional
          medical or food-safety advice.
        </p>
      </section>
    </div>
  )
}
