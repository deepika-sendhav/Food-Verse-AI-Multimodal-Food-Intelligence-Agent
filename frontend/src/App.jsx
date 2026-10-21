import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Skeleton from './components/Skeleton.jsx'

const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const FoodRecognition = lazy(() => import('./pages/FoodRecognition.jsx'))
const FreshnessDetector = lazy(() => import('./pages/FreshnessDetector.jsx'))
const HygieneMonitor = lazy(() => import('./pages/HygieneMonitor.jsx'))
const KitchenAssistant = lazy(() => import('./pages/KitchenAssistant.jsx'))
const MealPlanner = lazy(() => import('./pages/MealPlanner.jsx'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<main className="page-wrap"><Skeleton lines={5} /></main>}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="food-recognition" element={<FoodRecognition />} />
            <Route path="freshness-detector" element={<FreshnessDetector />} />
            <Route path="hygiene-monitor" element={<HygieneMonitor />} />
            <Route path="kitchen-assistant" element={<KitchenAssistant />} />
            <Route path="meal-planner" element={<MealPlanner />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
