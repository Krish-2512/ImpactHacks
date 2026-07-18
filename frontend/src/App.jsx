import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from './i18n'
import { useAuthStore } from './store/authStore'
import Navbar  from './components/layout/Navbar'
import AppInit from './components/AppInit'

import LandingPage       from './pages/LandingPage'
import LoginPage         from './pages/LoginPage'
import RegisterPage      from './pages/RegisterPage'
import DashboardPage     from './pages/DashboardPage'
import WeatherPage       from './pages/WeatherPage'
import MarketPage        from './pages/MarketPage'
import MarketplacePage   from './pages/MarketplacePage'
import DiseasePage       from './pages/DiseasePage'
import AdvisoryPage      from './pages/AdvisoryPage'
import NotificationsPage    from './pages/NotificationsPage'
import ProfilePage          from './pages/ProfilePage'
import CropRecommenderPage  from './pages/CropRecommenderPage'
import IrrigationPage       from './pages/IrrigationPage'
import TraceViewPage        from './pages/TraceViewPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
})

function Protected({ children }) {
  const token = useAuthStore(s => s.token)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>
        <BrowserRouter>
          <AppInit />
          <div className="min-h-screen bg-gray-50">
            <Navbar />
            <Routes>
              <Route path="/"            element={<LandingPage />} />
              <Route path="/login"       element={<LoginPage />} />
              <Route path="/register"    element={<RegisterPage />} />
              <Route path="/dashboard"   element={<Protected><DashboardPage /></Protected>} />
              <Route path="/weather"     element={<Protected><WeatherPage /></Protected>} />
              <Route path="/market"      element={<Protected><MarketPage /></Protected>} />
              <Route path="/marketplace" element={<Protected><MarketplacePage /></Protected>} />
              <Route path="/disease"     element={<Protected><DiseasePage /></Protected>} />
              <Route path="/advisory"    element={<Protected><AdvisoryPage /></Protected>} />
              <Route path="/notifications" element={<Protected><NotificationsPage /></Protected>} />
              <Route path="/profile"     element={<Protected><ProfilePage /></Protected>} />
              <Route path="/recommend"   element={<Protected><CropRecommenderPage /></Protected>} />
              <Route path="/irrigation"  element={<Protected><IrrigationPage /></Protected>} />
              <Route path="/trace/:cycleId" element={<Protected><TraceViewPage /></Protected>} />
              <Route path="*"            element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </BrowserRouter>
      </I18nextProvider>
    </QueryClientProvider>
  )
}
