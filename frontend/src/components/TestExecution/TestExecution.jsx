import { useState, useEffect } from 'react'
import { Button, Form, Input, Select, message, Card, Typography } from 'antd'
import { testExecutionApi, dataSensingApi } from '../../services/api'

const { Option } = Select
const { Title, Text } = Typography

function TestExecution() {
  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetchConfigs()
  }, [])

  const fetchConfigs = async () => {
    try {
      const response = await dataSensingApi.getAll()
      setConfigs(response.data)
    } catch (error) {
      message.error('获取数据感知配置失败')
    }
  }

  const handleSubmit = async (values) => {
    setLoading(true)
    try {
      const response = await testExecutionApi.simulateEvent({
        config_id: values.configId,
        data: JSON.parse(values.data || '{}')
      })
      setResult(response.data)
      message.success('事件模拟成功')
    } catch (error) {
      message.error('操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>测试执行</h2>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="configId" label="数据感知配置" rules={[{ required: true, message: '请选择配置' }]}>
            <Select>
              {configs.map((config) => (
                <Option key={config.id} value={config.id}>{config.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="data" label="事件数据 (JSON格式)" rules={[{ required: true, message: '请输入事件数据' }]}>
            <Input.TextArea rows={4} placeholder='例如: {"id": 1, "name": "测试数据"}' />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              模拟事件
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result && (
        <Card title="执行结果">
          <div>
            <Text strong>消息:</Text> {result.message}
          </div>
          <div style={{ marginTop: 8 }}>
            <Text strong>配置:</Text> {result.config}
          </div>
          <div style={{ marginTop: 8 }}>
            <Text strong>数据:</Text> {JSON.stringify(result.data)}
          </div>
        </Card>
      )}
    </div>
  )
}

export default TestExecution
