/**
 * WebSocket连接管理
 * 处理实时消息推送
 */

import { getToken } from './api'

export type WebSocketMessage = {
  type: 'connection' | 'new_message' | 'pong'
  status?: string
  message?: string
  data?: any
  timestamp?: string
}

export type MessageHandler = (message: WebSocketMessage) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectTimer: NodeJS.Timeout | null = null
  private pingTimer: NodeJS.Timeout | null = null
  private messageHandlers: Set<MessageHandler> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isManualClose = false
  private visibilityListenerActive = false

  connect() {
    // 允许disconnect()后再connect()正常工作
    this.isManualClose = false

    // 已连接或正在连接中,不重复创建
    if (this.ws) {
      const state = this.ws.readyState
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        return
      }
    }

    const token = getToken()
    if (!token) {
      console.warn('无token,跳过WebSocket连接')
      return
    }

    // 清理旧连接的事件处理器,防止泄漏
    this.cleanupWebSocket()

    try {
      // 根据当前页面地址动态构建WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      
      // 通过API_BASE_URL获取后端的域名和端口，这样可以确保 WebSocket 的目标和 HTTP API 保持一致
      const getBackendHost = () => {
        // Since Next.js proxy doesn't handle wss well out of the box in some configs,
        // and we know the backend is on 8000 when running locally:
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
           return `${window.location.hostname}:8000`
        }
        return window.location.host
      }

      const wsUrl = `${protocol}//${getBackendHost()}/api/v1/ws/${token}`
      console.log('WebSocket连接地址:', wsUrl)
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket连接成功')
        this.reconnectAttempts = 0
        this.startPing()
        this.startVisibilityListener()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          // 通知所有监听器
          this.messageHandlers.forEach(handler => {
            try {
              handler(message)
            } catch (err) {
              console.error('消息处理器错误:', err)
            }
          })
        } catch (err) {
          console.error('解析WebSocket消息失败:', err)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket连接关闭')
        this.stopPing()

        // 如果不是手动关闭,尝试重连
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`${this.reconnectDelay / 1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
          
          this.reconnectTimer = setTimeout(() => {
            this.connect()
          }, this.reconnectDelay)
        }
      }
    } catch (err) {
      console.error('创建WebSocket连接失败:', err)
    }
  }

  disconnect() {
    this.isManualClose = true
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.stopPing()
    this.stopVisibilityListener()
    this.cleanupWebSocket()
  }

  /** 清理旧WebSocket连接及其事件处理器 */
  private cleanupWebSocket() {
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onerror = null
      this.ws.onclose = null
      try {
        if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
          this.ws.close()
        }
      } catch { /* ignore */ }
      this.ws = null
    }
  }

  private startPing() {
    this.stopPing()
    
    // 每30秒发送一次心跳
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 30000)
  }

  private stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  // 页面可见性监听：手机锁屏/切后台后恢复时自动重连
  private handleVisibilityChange = () => {
    if (document.visibilityState === 'visible' && !this.isManualClose) {
      // 页面恢复可见时,检查连接状态
      const needsReconnect = !this.ws || 
        (this.ws.readyState !== WebSocket.OPEN && this.ws.readyState !== WebSocket.CONNECTING)
      
      if (needsReconnect && getToken()) {
        console.log('页面恢复可见,重新连接WebSocket')
        this.reconnectAttempts = 0
        this.connect()
      }
    }
  }

  private startVisibilityListener() {
    if (!this.visibilityListenerActive) {
      document.addEventListener('visibilitychange', this.handleVisibilityChange)
      this.visibilityListenerActive = true
    }
  }

  private stopVisibilityListener() {
    if (this.visibilityListenerActive) {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange)
      this.visibilityListenerActive = false
    }
  }

  addMessageHandler(handler: MessageHandler) {
    this.messageHandlers.add(handler)
  }

  removeMessageHandler(handler: MessageHandler) {
    this.messageHandlers.delete(handler)
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// 全局WebSocket管理器实例
export const wsManager = new WebSocketManager()
