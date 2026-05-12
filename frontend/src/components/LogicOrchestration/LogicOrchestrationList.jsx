import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Modal, Form, Input, message, Popconfirm, Tooltip, Typography, InputNumber, Select } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { orchestrationApi } from '../../services/api';
import './LogicOrchestration.css';

const { Text } = Typography;

const LogicOrchestrationList = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form] = Form.useForm();
  const [executeModalVisible, setExecuteModalVisible] = useState(false);
  const [executingItem, setExecutingItem] = useState(null);
  const [executeForm] = Form.useForm();
  const [executing, setExecuting] = useState(false);

  // 格式化时间，只显示到秒
  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    // 处理 ISO 格式时间，截取到秒（去除毫秒）
    const match = dateStr.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/);
    if (match) {
      return match[1];
    }
    return dateStr;
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await orchestrationApi.getAll();
      setData(res.data || []);
    } catch (err) {
      console.error('获取编排列表失败:', err);
      message.error('获取编排列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingItem(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingItem(record);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
    });
    setModalVisible(true);
  };

  const handleCanvas = (record) => {
    navigate(`/logic-orchestration/${record.id}`);
  };

  const handleDelete = async (id) => {
    try {
      await orchestrationApi.delete(id);
      message.success('删除成功');
      fetchData();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingItem) {
        await orchestrationApi.update(editingItem.id, values);
        message.success('更新成功');
        setModalVisible(false);
        fetchData();
      } else {
        const res = await orchestrationApi.create(values);
        const newId = res.data?.id;
        message.success('创建成功');
        setModalVisible(false);
        fetchData();
        if (newId) {
          navigate(`/logic-orchestration/${newId}`);
        }
      }
    } catch (err) {
      // 表单校验失败或其他错误
    }
  };

  const handleExecute = async (record) => {
    setExecutingItem(record);
    setExecuteModalVisible(true);
    try {
      const res = await orchestrationApi.get(record.id);
      const detail = res.data || {};
      const inputs = detail.graph_data?.inputs || [];
      setExecutingItem({ ...record, inputs });
      const initialValues = {};
      inputs.forEach(inp => {
        if (inp.defaultValue !== undefined && inp.defaultValue !== '') {
          initialValues[inp.name] = inp.defaultValue;
        }
      });
      setTimeout(() => {
        executeForm.setFieldsValue(initialValues);
      }, 0);
    } catch (err) {
      console.error('获取编排详情失败:', err);
    }
  };

  const handleExecuteConfirm = async () => {
    if (!executingItem) return;
    try {
      const values = await executeForm.validateFields();
      setExecuting(true);
      const res = await orchestrationApi.execute(executingItem.id, values);
      if (res.data?.success) {
        message.success('执行成功');
      } else {
        message.error(`执行失败: ${res.data?.error || '未知错误'}`);
      }
      setExecuteModalVisible(false);
    } catch (err) {
      if (err.errorFields) return; // 表单校验失败
      message.error('执行失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setExecuting(false);
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
      ellipsis: true,
      align: 'center',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text || '-'} placement="topLeft">
          <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {text || '-'}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 90,
      align: 'center',
      render: (text) => formatDateTime(text),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Space size={4}>
          <Button type="primary" size="small" onClick={() => handleCanvas(record)} style={{ marginRight: 0 }}>
            编辑
          </Button>
          <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleExecute(record)}>
            执行
          </Button>
          <Button size="small" onClick={() => handleEdit(record)}>
            编辑信息
          </Button>
          <Popconfirm
            title="确定删除？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="logic-orchestration-list-container" style={{ padding: '16px', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card
        title={<span style={{ fontSize: '16px', fontWeight: 600 }}>逻辑编排管理</span>}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新增编排
          </Button>
        }
        style={{ height: 'calc(100vh - 32px)' }}
        styles={{ body: { height: 'calc(100% - 57px)', overflow: 'auto', padding: '12px 16px' } }}
      >
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            size: 'small',
          }}
          scroll={{ y: 'calc(100vh - 280px)' }}
          size="small"
        />
      </Card>

      <Modal
        title={editingItem ? '编辑编排' : '新增编排'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="请输入编排名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`执行编排 - ${executingItem?.name || ''}`}
        open={executeModalVisible}
        onOk={handleExecuteConfirm}
        onCancel={() => setExecuteModalVisible(false)}
        okText="执行"
        cancelText="取消"
        confirmLoading={executing}
        width={520}
      >
        {(executingItem?.inputs || []).length > 0 ? (
          <Form form={executeForm} layout="vertical">
            {executingItem.inputs.map((inp) => (
              <Form.Item
                key={inp.name}
                name={inp.name}
                label={
                  <span>
                    {inp.name}
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      ({inp.type}{inp.required ? ', 必填' : ''})
                    </Text>
                  </span>
                }
                rules={inp.required ? [{ required: true, message: `请输入${inp.name}` }] : []}
                tooltip={inp.description || undefined}
                initialValue={inp.defaultValue || undefined}
              >
                {inp.type === 'number' || inp.type === 'integer' ? (
                  <InputNumber placeholder={`请输入${inp.name}`} style={{ width: '100%' }} />
                ) : inp.type === 'boolean' ? (
                  <Select placeholder={`请选择${inp.name}`} allowClear>
                    <Select.Option value={true}>true</Select.Option>
                    <Select.Option value={false}>false</Select.Option>
                  </Select>
                ) : (
                  <Input placeholder={`请输入${inp.name}`} />
                )}
              </Form.Item>
            ))}
          </Form>
        ) : (
          <div style={{ textAlign: 'center', padding: '24px 0', color: '#999' }}>
            该编排未定义入参，可直接执行
          </div>
        )}
      </Modal>
    </div>
  );
};

export default LogicOrchestrationList;
