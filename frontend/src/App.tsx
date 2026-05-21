import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import ChatPage from './pages/ChatPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import Layout from './components/Layout'
import { useAuthStore } from './store/authStore'

/**
 * 受保护路由 - 需要登录才能访问
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  const { loadFromStorage } = useAuthStore()

  useEffect(() => {
    loadFromStorage()
  }, [])

  return (
    <Router>
      <Routes>
        {/* 登录/注册 */}
        <Route path="/login" element={<LoginPage />} />

        {/* 用户端 - 聊天界面（需要登录） */}
        <Route path="/chat" element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        } />

        {/* 管理后台（需要登录） */}
        <Route path="/admin" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index element={<AdminPage />} />
          <Route path="knowledge" element={<AdminPage />} />
          <Route path="sessions" element={<AdminPage />} />
          <Route path="logs" element={<AdminPage />} />
        </Route>

        {/* 默认跳转到聊天页 */}
        <Route path="/" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Router>
  )
}

export default App
