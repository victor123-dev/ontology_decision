import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'

import './App.css'

// 导入组件
import DataSource from './components/DataSource/DataSource'
import BusinessModel from './components/BusinessModel/BusinessModel'
import DataSensing from './components/DataSensing/DataSensing'
import DriveLogic from './components/DriveLogic/DriveLogic'
import Agent from './components/Agent/Agent'
import TestData from './components/TestData/TestData'
import DriveLog from './components/DriveLog/DriveLog'
import TestExecution from './components/TestExecution/TestExecution'
import DocumentImport from './components/DocumentImport/DocumentImport'
import DriveVisualization from './components/DriveVisualization/DriveVisualization'

const { Header, Sider, Content } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const { token: { colorBgContainer } } = theme.useToken()

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider trigger={null} collapsible collapsed={collapsed}>
          <div className="logo" />
          <Menu
            theme="dark"
            mode="inline"
            defaultSelectedKeys={['data-source']}
            items={[
              {
                key: 'group-1',
                label: '基础数据配置',
                type: 'group',
                children: [
                  {
                    key: 'data-source',
                    icon: <span>📊</span>,
                    label: <Link to="/data-source">数据源管理</Link>,
                  },
                  {
                    key: 'business-model',
                    icon: <span>🏗️</span>,
                    label: <Link to="/business-model">业务模型管理</Link>,
                  },
                  {
                    key: 'test-data',
                    icon: <span>📝</span>,
                    label: <Link to="/test-data">测试数据管理</Link>,
                  }
                ]
              },
              {
                key: 'group-2',
                label: '智能体管理',
                type: 'group',
                children: [
                  {
                    key: 'agent',
                    icon: <span>🤖</span>,
                    label: <Link to="/agent">Agent管理</Link>,
                  }
                ]
              },
              {
                key: 'group-3',
                label: '核心驱动配置',
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
                  }
                ]
              },
              {
                key: 'group-4',
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
                key: 'group-5',
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
        <Layout>
          <Header
            style={{
              background: colorBgContainer,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 24px',
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>数据驱动项目系统</div>
            <button
              type="button"
              className="trigger"
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: 64,
                height: 64,
              }}
            >
              {collapsed ? '展开' : '收起'}
            </button>
          </Header>
          <Content
            style={{
              margin: '24px 16px',
              padding: 24,
              minHeight: 280,
              background: colorBgContainer,
            }}
          >
            <Routes>
              <Route path="/data-source" element={<DataSource />} />
              <Route path="/business-model" element={<BusinessModel />} />
              <Route path="/test-data" element={<TestData />} />
              <Route path="/agent" element={<Agent />} />
              <Route path="/document-import" element={<DocumentImport />} />
              <Route path="/data-sensing" element={<DataSensing />} />
              <Route path="/drive-logic" element={<DriveLogic />} />
              <Route path="/test-execution" element={<TestExecution />} />
              <Route path="/drive-log" element={<DriveLog />} />
              <Route path="/drive-visualization" element={<DriveVisualization />} />
              <Route path="/" element={<DataSource />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  )
}

export default App
