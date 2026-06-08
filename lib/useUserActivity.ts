/**
 * 用户活跃状态管理Hook
 * 定期发送心跳,保持在线状态
 */
import { useEffect } from 'react'
import { authApi, getToken } from './api'

const HEARTBEAT_INTERVAL = 2 * 60 * 1000 // 2分钟发送一次心跳

export function useUserActivity() {
  useEffect(() => {
    // 发送心跳
    const sendHeartbeat = async () => {
      // 只有在已登录时才发送心跳
      if (!getToken()) {
        return
      }
      try {
        await authApi.heartbeat()
      } catch (error) {
        console.error('发送心跳失败:', error)
      }
    }

    // 立即发送一次
    sendHeartbeat()

    // 定期发送心跳
    const intervalId = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL)

    return () => {
      clearInterval(intervalId)
    }
  }, [])
}
