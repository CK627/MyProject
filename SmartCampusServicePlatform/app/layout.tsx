import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '智慧校园服务平台',
  description: '一站式智慧校园服务平台 - 学校介绍、互帮互助、校园墙、公告、好友、支付系统等',
  keywords: '智慧校园,校园服务,学生服务,校园墙,互帮互助',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' }}>
        {children}
      </body>
    </html>
  )
}

