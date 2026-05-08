import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Modal, Form, Input, message, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { orchestrationApi } from '../../services/api';
import './LogicOrchestration.css';

const LogicOrchestrationList = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form] = Form.useForm();

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
      width: 80,
      align: 'center',
      render: (text) => text || '-',
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
        bodyStyle={{ height: 'calc(100% - 57px)', overflow: 'auto', padding: '12px 16px' }}
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
    </div>
  );
};

export default LogicOrchestrationList;
