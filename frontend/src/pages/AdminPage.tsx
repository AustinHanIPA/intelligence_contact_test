/**
 * 管理后台页面 - 知识库运营 & 数据监控
 */
import { useState, useEffect } from 'react'
import { knowledgeApi, adminApi } from '../services/api'
import './AdminPage.css'

interface DashboardData {
  total_sessions: number
  active_sessions: number
  handoff_sessions: number
  total_conversations: number
}

interface KnowledgeItem {
  id: number
  knowledge_id: string
  title: string
  type: string
  domain: string
  status: string
  hit_count: number
  updated_at: string
}

function AdminPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'knowledge' | 'logs'>('dashboard')
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      const data: any = await adminApi.dashboard()
      setDashboard(data)
    } catch (e) {
      console.error('Failed to load dashboard', e)
    } finally {
      setLoading(false)
    }
  }

  const loadKnowledge = async () => {
    try {
      setLoading(true)
      const data: any = await knowledgeApi.list({ page: 1, page_size: 50 })
      setKnowledgeList(data.items || [])
    } catch (e) {
      console.error('Failed to load knowledge', e)
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (tab: 'dashboard' | 'knowledge' | 'logs') => {
    setActiveTab(tab)
    if (tab === 'knowledge') loadKnowledge()
    if (tab === 'dashboard') loadDashboard()
  }

  return (
    <div className="admin-page">
      <div className="admin-sidebar">
        <div className="admin-logo">
          <span className="logo-icon">&#x1F916;</span>
          <h3>智能客服管理</h3>
        </div>
        <nav className="admin-nav">
          <button
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => handleTabChange('dashboard')}
          >
            数据概览
          </button>
          <button
            className={activeTab === 'knowledge' ? 'active' : ''}
            onClick={() => handleTabChange('knowledge')}
          >
            知识库管理
          </button>
          <button
            className={activeTab === 'logs' ? 'active' : ''}
            onClick={() => handleTabChange('logs')}
          >
            对话日志
          </button>
        </nav>
      </div>

      <div className="admin-content">
        {loading && <div className="admin-loading">加载中...</div>}

        {activeTab === 'dashboard' && dashboard && (
          <DashboardView data={dashboard} />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeView items={knowledgeList} onRefresh={loadKnowledge} />
        )}

        {activeTab === 'logs' && <LogsView />}
      </div>
    </div>
  )
}

function DashboardView({ data }: { data: DashboardData }) {
  return (
    <div className="dashboard-view">
      <h2>数据概览</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{data.total_sessions}</div>
          <div className="stat-label">总会话数</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{data.active_sessions}</div>
          <div className="stat-label">活跃会话</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-number">{data.handoff_sessions}</div>
          <div className="stat-label">转人工数</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{data.total_conversations}</div>
          <div className="stat-label">总对话数</div>
        </div>
      </div>

      <div className="dashboard-section">
        <h3>系统状态</h3>
        <div className="status-list">
          <div className="status-item">
            <span className="status-dot green"></span>
            <span>知识库服务</span>
            <span className="status-text">正常</span>
          </div>
          <div className="status-item">
            <span className="status-dot green"></span>
            <span>NLU服务</span>
            <span className="status-text">正常</span>
          </div>
          <div className="status-item">
            <span className="status-dot green"></span>
            <span>规则引擎</span>
            <span className="status-text">正常</span>
          </div>
          <div className="status-item">
            <span className="status-dot green"></span>
            <span>工具调用服务</span>
            <span className="status-text">正常</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function KnowledgeView({ items, onRefresh }: { items: KnowledgeItem[]; onRefresh: () => void }) {
  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; className: string }> = {
      active: { label: '已上线', className: 'badge-success' },
      draft: { label: '草稿', className: 'badge-default' },
      reviewing: { label: '审核中', className: 'badge-warning' },
      offline: { label: '已下线', className: 'badge-error' },
    }
    return map[status] || { label: status, className: 'badge-default' }
  }

  const getTypeName = (type: string) => {
    const map: Record<string, string> = {
      faq: 'FAQ',
      policy: '政策',
      sop: 'SOP',
      product: '商品',
      tool_desc: '工具说明',
    }
    return map[type] || type
  }

  return (
    <div className="knowledge-view">
      <div className="view-header">
        <h2>知识库管理</h2>
        <div className="view-actions">
          <button className="btn-default" onClick={onRefresh}>刷新</button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <p>暂无知识条目，请通过API添加知识或等待系统初始化。</p>
        </div>
      ) : (
        <div className="knowledge-table">
          <table>
            <thead>
              <tr>
                <th>标题</th>
                <th>类型</th>
                <th>领域</th>
                <th>状态</th>
                <th>命中次数</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const badge = getStatusBadge(item.status)
                return (
                  <tr key={item.knowledge_id}>
                    <td className="title-cell">{item.title}</td>
                    <td>{getTypeName(item.type)}</td>
                    <td>{item.domain}</td>
                    <td>
                      <span className={`badge ${badge.className}`}>{badge.label}</span>
                    </td>
                    <td>{item.hit_count}</td>
                    <td>{new Date(item.updated_at).toLocaleDateString('zh-CN')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function LogsView() {
  const [logs, setLogs] = useState<any[]>([])

  useEffect(() => {
    loadLogs()
  }, [])

  const loadLogs = async () => {
    try {
      const data: any = await adminApi.conversationLogs({ page: 1 })
      setLogs(data.items || [])
    } catch (e) {
      console.error('Failed to load logs', e)
    }
  }

  return (
    <div className="logs-view">
      <div className="view-header">
        <h2>对话日志</h2>
        <button className="btn-default" onClick={loadLogs}>刷新</button>
      </div>

      {logs.length === 0 ? (
        <div className="empty-state">
          <p>暂无对话日志。用户开始对话后，日志将在这里显示。</p>
        </div>
      ) : (
        <div className="logs-table">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>用户消息</th>
                <th>识别意图</th>
                <th>选择动作</th>
                <th>响应时间</th>
                <th>反馈</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.log_id}>
                  <td>{log.created_at ? new Date(log.created_at).toLocaleString('zh-CN') : '-'}</td>
                  <td className="message-cell">{log.user_message}</td>
                  <td>{log.detected_intent || '-'}</td>
                  <td>{log.selected_action || '-'}</td>
                  <td>{log.response_time_ms ? `${log.response_time_ms}ms` : '-'}</td>
                  <td>{log.user_feedback || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default AdminPage
