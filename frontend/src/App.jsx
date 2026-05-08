import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'

import './App.css'

// 导入组件
import DataSource from './components/DataSource/DataSource'
import BusinessModel from './components/BusinessModel/BusinessModel'
import DataSensing from './components/DataSensing/DataSensing'
import DriveLogic from './components/DriveLogic/DriveLogic'
import BusinessData from './components/BusinessData/BusinessData'
import DriveLog from './components/DriveLog/DriveLog'
import TestExecution from './components/TestExecution/TestExecution'
import DocumentImport from './components/DocumentImport/DocumentImport'
import DriveVisualization from './components/DriveVisualization/DriveVisualization'
import AlertDashboard from './components/AlertDashboard/AlertDashboard'
import LogicOrchestration from './components/LogicOrchestration/LogicOrchestrationList'
import LogicOrchestrationCanvas from './components/LogicOrchestration/LogicOrchestrationCanvas'
import { AgentButton, AgentPanel } from './components/AgentDialog'

const { Header, Sider, Content } = Layout

function AppContent() {
  const [collapsed, setCollapsed] = useState(false)
  const [agentPanelVisible, setAgentPanelVisible] = useState(false)
  const { token: { colorBgContainer } } = theme.useToken()
  const location = useLocation()
  
  // 根据当前路径设置选中的菜单项
  const getCurrentSelectedKey = () => {
    const path = location.pathname
    if (path === '/') return 'alert-dashboard'
    return path.substring(1) // 移除开头的 '/'
  }

  const selectedKey = getCurrentSelectedKey()

  return (
    <Layout style={{ minHeight: '100vh', width: '100%' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} style={{ marginRight: '1px' }}>
        <div className="logo" />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={[
            {
              key: 'group-0',
              label: '业务看板',
              type: 'group',
              children: [
                {
                  key: 'alert-dashboard',
                  icon: <span>⚠️</span>,
                  label: <Link to="/alert-dashboard">预警看板</Link>,
                }
              ]
            },
            {
              key: 'group-1',
              label: '基础数据配置',
              type: 'group',
              children: [
                {
                  key: 'data-source',
                  icon: <span>📊</span>,
                  label: <Link to="/data-source">数据采集</Link>,
                },
                {
                  key: 'business-model',
                  icon: <span>🏗️</span>,
                  label: <Link to="/business-model">业务模型管理</Link>,
                },
                {
                  key: 'business-data',
                  icon: <span>📝</span>,
                  label: <Link to="/business-data">业务数据管理</Link>,
                }
              ]
            },
            {
              key: 'group-2',
              label: '数据驱动配置',
              type: 'group',
              children: [
                {
                  key: 'document-import',
                  icon: <span>📄</span>,
                  label: <Link to="/document-import">文档导入</Link>,
                },
                {
                  key: 'data-sensing',
                  icon: <span>🔍</span>,
                  label: <Link to="/data-sensing">数据感知配置</Link>,
                },
                {
                  key: 'drive-logic',
                  icon: <span>⚙️</span>,
                  label: <Link to="/drive-logic">驱动逻辑配置</Link>,
                },
                {
                  key: 'logic-orchestration',
                  icon: <span>🔗</span>,
                  label: <Link to="/logic-orchestration">逻辑编排</Link>,
                }
              ]
            },
            {
              key: 'group-3',
              label: '测试监控',
              type: 'group',
              children: [
                {
                  key: 'test-execution',
                  icon: <span>🧪</span>,
                  label: <Link to="/test-execution">测试执行</Link>,
                },
                {
                  key: 'drive-log',
                  icon: <span>📋</span>,
                  label: <Link to="/drive-log">驱动日志</Link>,
                }
              ]
            },
            {
              key: 'group-4',
              label: '可视化分析',
              type: 'group',
              children: [
                {
                  key: 'drive-visualization',
                  icon: <span>📈</span>,
                  label: <Link to="/drive-visualization">驱动可视化</Link>,
                }
              ]
            }
          ]}
        />
      </Sider>
      <Layout style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', marginLeft: '1px' }}>
        <Content
          style={{
            padding: '0',
            margin: '0',
            background: 'transparent',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Routes>
            <Route path="/data-source" element={<DataSource />} />
            <Route path="/business-model" element={<BusinessModel />} />
            <Route path="/business-data" element={<BusinessData />} />
            <Route path="/document-import" element={<DocumentImport />} />
            <Route path="/data-sensing" element={<DataSensing />} />
            <Route path="/drive-logic" element={<DriveLogic />} />
            <Route path="/test-execution" element={<TestExecution />} />
            <Route path="/drive-log" element={<DriveLog />} />
            <Route path="/drive-visualization" element={<DriveVisualization />} />
            <Route path="/alert-dashboard" element={<AlertDashboard />} />
            <Route path="/logic-orchestration" element={<LogicOrchestration />} />
            <Route path="/logic-orchestration/:id" element={<LogicOrchestrationCanvas />} />
            <Route path="/" element={<AlertDashboard />} />
          </Routes>
        </Content>
      </Layout>
      <AgentPanel 
        visible={agentPanelVisible} 
        onClose={() => setAgentPanelVisible(false)} 
      />
      <AgentButton 
        onClick={() => setAgentPanelVisible(true)}
        isVisible={!agentPanelVisible}
      />
    </Layout>
  )
}

function App() {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AppContent />
    </Router>
  )
}

export default App
