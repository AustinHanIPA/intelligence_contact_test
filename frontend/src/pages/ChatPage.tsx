/**
 * 用户聊天页面 - 智能客服对话界面
 */
import { useState, useRef, useEffect } from 'react'
import { useChatStore, Message } from '../store/chatStore'
import './ChatPage.css'

function ChatPage() {
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, isLoading, error, sendMessage, executeAction, clearMessages } = useChatStore()

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const content = inputValue.trim()
    if (!content || isLoading) return
    setInputValue('')
    await sendMessage(content)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleActionClick = async (action: string, params?: Record<string, any>) => {
    await executeAction(action, params)
  }

  const handleQuickAction = async (action: string) => {
    const quickMessages: Record<string, string> = {
      order: '我想查询订单',
      logistics: '帮我查一下物流',
      refund: '我要申请退款',
      human: '转人工客服',
    }
    await sendMessage(quickMessages[action] || action)
  }

  return (
    <div className="chat-page">
      {/* 头部 */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-avatar">🤖</div>
          <div className="chat-title">
            <h3>智能客服</h3>
            <span className="chat-status">在线</span>
          </div>
        </div>
        <button className="chat-clear-btn" onClick={clearMessages}>
          清空对话
        </button>
      </div>

      {/* 消息区域 */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <div className="welcome-icon">👋</div>
            <h2>您好，我是智能客服助手</h2>
            <p>我可以帮您查询订单、物流、申请退款等。请问有什么可以帮您的？</p>
            <div className="quick-actions">
              <button onClick={() => handleQuickAction('order')}>📦 查询订单</button>
              <button onClick={() => handleQuickAction('logistics')}>🚚 查询物流</button>
              <button onClick={() => handleQuickAction('refund')}>💰 申请退款</button>
              <button onClick={() => handleQuickAction('human')}>👤 转人工</button>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onActionClick={handleActionClick}
          />
        ))}

        {isLoading && (
          <div className="message-bubble assistant">
            <div className="bubble-content">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="chat-error">
            <span>⚠️ {error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="请输入您的问题..."
            rows={1}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}

// 消息气泡组件
function MessageBubble({
  message,
  onActionClick,
}: {
  message: Message
  onActionClick: (action: string, params?: Record<string, any>) => void
}) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  return (
    <div className={`message-bubble ${message.role}`}>
      {!isUser && <div className="bubble-avatar">{isSystem ? '⚙️' : '🤖'}</div>}
      <div className="bubble-wrapper">
        <div className="bubble-content">
          <div className="bubble-text" style={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </div>

          {/* 操作按钮 */}
          {message.buttons && message.buttons.length > 0 && (
            <div className="bubble-actions">
              {message.buttons.map((btn, idx) => (
                <button
                  key={idx}
                  className="action-btn"
                  onClick={() => onActionClick(btn.action, btn.params)}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          )}

          {/* 转人工提示 */}
          {message.handoff && (
            <div className="handoff-notice">
              🔄 正在为您转接人工客服...
            </div>
          )}
        </div>

        <div className="bubble-meta">
          {message.intent && <span className="meta-intent">#{message.intent}</span>}
          <span className="meta-time">
            {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
      {isUser && <div className="bubble-avatar user-avatar">👤</div>}
    </div>
  )
}

export default ChatPage
