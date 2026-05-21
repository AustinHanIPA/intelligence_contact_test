import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import AdminPage from './pages/AdminPage'
import Layout from './components/Layout'

function App() {
  return (
    <Router>
      <Routes>
        {/* 用户端 - 聊天界面 */}
        <Route path="/chat" element={<ChatPage />} />

        {/* 管理后台 */}
        <Route path="/admin" element={<Layout />}>
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
