import { useState, useEffect } from 'react';
import { Card, Upload, Button, message, Spin, Steps, Modal, Table, Tag, Form, Input, Select, Popconfirm, Typography } from 'antd';
import { InboxOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Dragger } = Upload;
const { Step } = Steps;
const { Option } = Select;
const { Text } = Typography;

const DocumentImport = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [documentContent, setDocumentContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [configs, setConfigs] = useState({ sensing_configs: [], drive_logics: [] });
  const [loading, setLoading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [editingSensingConfig, setEditingSensingConfig] = useState(null);
  const [editingDriveLogic, setEditingDriveLogic] = useState(null);
  const [sensingModalVisible, setSensingModalVisible] = useState(false);
  const [driveLogicModalVisible, setDriveLogicModalVisible] = useState(false);
  const [sensingForm] = Form.useForm();
  const [driveLogicForm] = Form.useForm();
  
  // 新增状态：业务模型和行动数据
  const [businessModels, setBusinessModels] = useState([]);
  const [actions, setActions] = useState([]);
  
  // 类型相关的状态
  const [selectedSensingType, setSelectedSensingType] = useState('data_change');
  const [selectedDriveLogicType, setSelectedDriveLogicType] = useState('first_order');

  useEffect(() => {
    // 获取业务模型和行动数据
    fetchBusinessModelsAndActions();
  }, []);

  const fetchBusinessModelsAndActions = async () => {
    try {
      // 获取业务模型
      const businessModelResponse = await api.get('/business-models');
      setBusinessModels(businessModelResponse.data || []);
      
      // 获取行动
      const actionResponse = await api.get('/actions');
      setActions(actionResponse.data || []);
      
      // 设置当前的感知配置用于驱动逻辑选择
        // setSensingConfigs(configs.sensing_configs || []);
    } catch (error) {
      console.error('获取业务模型或行动数据失败:', error);
      message.error('获取业务模型或行动数据失败');
    }
  };

  const handleFileUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const response = await api.post('/document-import/parse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setDocumentContent(response.data.content);
      setFileName(response.data.filename);
      setCurrentStep(1);
      message.success('文档解析成功');
    } catch (error) {
      console.error('文档解析失败:', error);
      message.error('文档解析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateConfigs = async () => {
    const formData = new FormData();
    formData.append('document_content', documentContent);

    setLoading(true);
    try {
      const response = await api.post('/document-import/generate-configs', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setConfigs(response.data);
      setCurrentStep(2);
      message.success('配置生成成功');
    } catch (error) {
      console.error('配置生成失败:', error);
      message.error('配置生成失败');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyConfigs = async () => {
    const requestData = {
      sensing_configs: configs.sensing_configs,
      drive_logics: configs.drive_logics
    };

    setLoading(true);
    try {
      await api.post('/document-import/apply-configs', requestData);
      message.success('配置应用成功');
      setCurrentStep(0);
      setDocumentContent('');
      setFileName('');
      setConfigs({ sensing_configs: [], drive_logics: [] });
    } catch (error) {
      console.error('配置应用失败:', error);
      message.error('配置应用失败');
    } finally {
      setLoading(false);
    }
  };

  const showPreview = () => {
    setPreviewVisible(true);
  };

  // 数据感知配置表格列定义
  const sensingColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <span>{text || '-'}</span>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        return type === 'data_change' ? '数据变化感知' : 
               type === 'threshold' ? '阈值触发感知' : type || '-';
      }
    },
    {
      title: '业务模型',
      dataIndex: 'model_id',
      key: 'model_id',
      render: (modelId) => {
        const model = businessModels.find(m => m.id === modelId);
        return model ? model.name : modelId || '-';
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record, index) => (
        <div>
          <Button 
            type="primary" 
            size="small" 
            icon={<EditOutlined />} 
            style={{ marginRight: 8 }}
            onClick={() => handleEditSensingConfig(record, index)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个配置吗？"
            onConfirm={() => handleDeleteSensingConfig(index)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </div>
      ),
    },
  ];

  // 驱动逻辑配置表格列定义
  const driveLogicColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <span>{text || '-'}</span>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        return type === 'first_order' 
          ? <Tag color="blue">一阶函数</Tag> 
          : type === 'script' 
          ? <Tag color="green">脚本函数</Tag>
          : type || '-';
      }
    },
    {
      title: '关联事件',
      dataIndex: 'event_temp_ids',
      key: 'event_temp_ids',
      render: (eventTempIds) => {
        if (!eventTempIds || eventTempIds.length === 0) return '-';
        return eventTempIds.map((tempId, idx) => {
          const config = configs.sensing_configs.find(c => c.temp_id === tempId);
          return <Tag key={idx} color="purple">{config ? config.name : tempId}</Tag>;
        });
      }
    },
    {
      title: '关联行动',
      dataIndex: 'action_ids',
      key: 'action_ids',
      render: (actionIds) => {
        if (!actionIds || actionIds.length === 0) return '-';
        return actionIds.map((actionId, idx) => {
          const action = actions.find(a => a.id === actionId);
          return <Tag key={idx} color="cyan">{action ? action.name : actionId}</Tag>;
        });
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record, index) => (
        <div>
          <Button 
            type="primary" 
            size="small" 
            icon={<EditOutlined />} 
            style={{ marginRight: 8 }}
            onClick={() => handleEditDriveLogic(record, index)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个配置吗？"
            onConfirm={() => handleDeleteDriveLogic(index)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </div>
      ),
    },
  ];

  // 处理编辑数据感知配置
  const handleEditSensingConfig = (record, index) => {
    setEditingSensingConfig({ ...record, index });
    
    // 将嵌套的config字段展开为扁平化字段
    const formValues = {
      ...record,
      ...record.config
    };
    sensingForm.setFieldsValue(formValues);
    setSensingModalVisible(true);
  };

  // 处理删除数据感知配置
  const handleDeleteSensingConfig = (index) => {
    const newConfigs = [...configs.sensing_configs];
    newConfigs.splice(index, 1);
    setConfigs({ ...configs, sensing_configs: newConfigs });
    message.success('删除成功');
  };

  // 处理新增数据感知配置
  const handleAddSensingConfig = () => {
    setEditingSensingConfig(null);
    sensingForm.resetFields();
    setSensingModalVisible(true);
  };

  // 处理保存数据感知配置
  const handleSaveSensingConfig = async (values) => {
    // 提取config相关的字段
    const { 
      trigger_conditions, monitored_fields, check_interval,
      monitored_field, threshold_type, threshold_value, threshold_field, operator,
      ...otherValues 
    } = values;
    
    const config = {};
    if (values.type === 'data_change') {
      config.trigger_conditions = trigger_conditions || [];
      config.monitored_fields = monitored_fields || [];
      config.check_interval = check_interval || 5;
    } else if (values.type === 'threshold') {
      config.monitored_field = monitored_field || '';
      config.threshold_type = threshold_type || 'static';
      if (threshold_type === 'static') {
        config.threshold_value = threshold_value;
      } else {
        config.threshold_field = threshold_field;
      }
      config.operator = operator || 'gt';
      config.check_interval = check_interval || 5;
    }
    
    const newConfigs = [...configs.sensing_configs];
    if (editingSensingConfig) {
      // 编辑
      newConfigs[editingSensingConfig.index] = { 
        ...editingSensingConfig, 
        ...otherValues,
        config 
      };
      message.success('编辑成功');
    } else {
      // 新增
      newConfigs.push({ 
        ...otherValues, 
        config,
        temp_id: `temp_${newConfigs.length}` 
      });
      message.success('新增成功');
    }
    setConfigs({ ...configs, sensing_configs: newConfigs });
    setSensingModalVisible(false);
  };

  // 处理编辑驱动逻辑配置
  const handleEditDriveLogic = (record, index) => {
    setEditingDriveLogic({ ...record, index });
    
    // 将嵌套的config字段展开为扁平化字段
    const formValues = {
      ...record,
      ...record.config
    };
    driveLogicForm.setFieldsValue(formValues);
    setDriveLogicModalVisible(true);
  };

  // 处理删除驱动逻辑配置
  const handleDeleteDriveLogic = (index) => {
    const newConfigs = [...configs.drive_logics];
    newConfigs.splice(index, 1);
    setConfigs({ ...configs, drive_logics: newConfigs });
    message.success('删除成功');
  };

  // 处理新增驱动逻辑配置
  const handleAddDriveLogic = () => {
    setEditingDriveLogic(null);
    driveLogicForm.resetFields();
    setDriveLogicModalVisible(true);
  };

  // 处理保存驱动逻辑配置
  const handleSaveDriveLogic = async (values) => {
    // 处理数组输入
    const processedValues = { ...values };
    if (values.event_temp_ids && typeof values.event_temp_ids === 'string') {
      processedValues.event_temp_ids = values.event_temp_ids.split(',').map(id => id.trim()).filter(id => id);
    }
    if (values.action_ids && typeof values.action_ids === 'string') {
      processedValues.action_ids = values.action_ids.split(',').map(id => id.trim()).filter(id => id);
    }
    
    // 提取config相关的字段
    const { 
      pre_condition, script_content,
      ...otherValues 
    } = processedValues;
    
    const config = {};
    if (values.type === 'first_order') {
      config.pre_condition = pre_condition || '';
    } else if (values.type === 'script') {
      config.script_content = script_content || '';
    }
    
    const newConfigs = [...configs.drive_logics];
    if (editingDriveLogic) {
      // 编辑
      newConfigs[editingDriveLogic.index] = { 
        ...editingDriveLogic, 
        ...otherValues,
        config 
      };
      message.success('编辑成功');
    } else {
      // 新增
      newConfigs.push({ 
        ...otherValues, 
        config,
        temp_id: `temp_${newConfigs.length}` 
      });
      message.success('新增成功');
    }
    setConfigs({ ...configs, drive_logics: newConfigs });
    setDriveLogicModalVisible(false);
  };

  const steps = [
    {
      title: '上传文档',
      content: (
        <div>
          <Dragger 
            beforeUpload={(file) => {
              handleFileUpload(file);
              return false; // 阻止自动上传
            }}
            accept=".pdf,.docx,.txt"
            showUploadList={false}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持PDF、Word、TXT格式</p>
          </Dragger>
          {fileName && (
            <div style={{ marginTop: 16 }}>
              <Text strong>已选择文件:</Text> {fileName}
            </div>
          )}
        </div>
      )
    },
    {
      title: '生成配置',
      content: (
        <div>
          <Button type="primary" onClick={handleGenerateConfigs} loading={loading}>
            生成配置
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => setCurrentStep(0)}>
            返回重新上传
          </Button>
          {documentContent && (
            <Button style={{ marginLeft: 8 }} onClick={showPreview}>
              预览文档内容
            </Button>
          )}
        </div>
      )
    },
    {
      title: '确认应用',
      content: (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4>数据感知配置 ({configs.sensing_configs.length} 个)</h4>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddSensingConfig}>
              添加配置
            </Button>
          </div>
          <Table 
            columns={sensingColumns} 
            dataSource={configs.sensing_configs} 
            rowKey={(record, index) => `sensing_${index}`}
            pagination={false}
          />
          
          <div style={{ marginTop: 24, marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4>驱动逻辑配置 ({configs.drive_logics.length} 个)</h4>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddDriveLogic}>
              添加配置
            </Button>
          </div>
          <Table 
            columns={driveLogicColumns} 
            dataSource={configs.drive_logics} 
            rowKey={(record, index) => `logic_${index}`}
            pagination={false}
          />
          
          <div style={{ marginTop: 16 }}>
            <Button type="primary" onClick={handleApplyConfigs} loading={loading}>
              应用配置
            </Button>
            <Button style={{ marginLeft: 8 }} onClick={() => setCurrentStep(1)}>
              返回重新生成
            </Button>
          </div>
        </div>
      )
    }
  ];

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div style={{ marginBottom: 16 }}>
        <h2>文档导入规则配置</h2>
        <p>通过上传业务文档，系统将自动解析并生成数据感知配置和驱动逻辑规则</p>
      </div>
      
      <Card>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          {steps.map((step) => (
            <Step key={step.title} title={step.title} />
          ))}
        </Steps>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : (
          steps[currentStep].content
        )}
      </Card>
      
      <Modal
        title={`文档内容预览 - ${fileName}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        <div style={{ maxHeight: '60vh', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
          {documentContent}
        </div>
      </Modal>

      {/* 数据感知配置编辑/新增模态框 */}
      <Modal
        title={editingSensingConfig ? '编辑数据感知配置' : '添加数据感知配置'}
        open={sensingModalVisible}
        onOk={() => sensingForm.submit()}
        onCancel={() => setSensingModalVisible(false)}
        width={600}
        afterOpenChange={(open) => {
          if (open && editingSensingConfig) {
            // 设置类型状态
            setSelectedSensingType(editingSensingConfig.type || 'data_change');
          }
        }}
      >
        <Form 
          form={sensingForm} 
          layout="vertical" 
          onFinish={handleSaveSensingConfig}
          onValuesChange={(changedValues) => {
            if (changedValues.type) {
              setSelectedSensingType(changedValues.type);
            }
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select>
              <Option value="data_change">数据变化感知</Option>
              <Option value="threshold">阈值触发感知</Option>
            </Select>
          </Form.Item>
          <Form.Item name="model_id" label="业务模型" rules={[{ required: true, message: '请选择业务模型' }]}>
            <Select placeholder="请选择业务模型">
              {businessModels.map((model) => (
                <Option key={model.id} value={model.id}>{model.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          {/* 数据变化感知配置 */}
          {selectedSensingType === 'data_change' && (
            <div>
              <Form.Item 
                name="trigger_conditions" 
                label="触发条件" 
                rules={[{ required: true, message: '请选择触发条件' }]}
              >
                <Select mode="multiple" placeholder="选择触发条件">
                  <Option value="create">新增</Option>
                  <Option value="update">更新</Option>
                  <Option value="delete">删除</Option>
                </Select>
              </Form.Item>
              <Form.Item 
                name="monitored_fields" 
                label="监控字段" 
                rules={[{ required: true, message: '请选择监控字段' }]}
              >
                <Select mode="multiple" placeholder="选择监控字段">
                  {businessModels
                    .find(model => model.id === sensingForm.getFieldValue('model_id'))?.fields
                    ?.map((field) => (
                      <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                    )) || []}
                </Select>
              </Form.Item>
              <Form.Item name="check_interval" label="检查间隔 (秒)" initialValue={5}>
                <Input type="number" min={1} max={60} />
              </Form.Item>
            </div>
          )}
          
          {/* 阈值触发感知配置 */}
          {selectedSensingType === 'threshold' && (
            <div>
              <Form.Item 
                name="monitored_field" 
                label="监控字段" 
                rules={[{ required: true, message: '请选择监控字段' }]}
              >
                <Select placeholder="选择监控字段">
                  {businessModels
                    .find(model => model.id === sensingForm.getFieldValue('model_id'))?.fields
                    ?.map((field) => (
                      <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                    )) || []}
                </Select>
              </Form.Item>
              <Form.Item name="threshold_type" label="阈值类型" initialValue="static">
                <Select>
                  <Option value="static">固定阈值</Option>
                  <Option value="dynamic">动态阈值</Option>
                </Select>
              </Form.Item>
              <Form.Item 
                noStyle 
                shouldUpdate={(prevValues, currentValues) => prevValues.threshold_type !== currentValues.threshold_type}
              >
                {({ getFieldValue }) => {
                  const thresholdType = getFieldValue('threshold_type');
                  if (thresholdType === 'static') {
                    return (
                      <Form.Item 
                        name="threshold_value" 
                        label="固定阈值" 
                        rules={[{ required: true, message: '请输入固定阈值' }]}
                      >
                        <Input type="number" placeholder="例如: 100" />
                      </Form.Item>
                    );
                  }
                  if (thresholdType === 'dynamic') {
                    return (
                      <Form.Item 
                        name="threshold_field" 
                        label="阈值字段" 
                        rules={[{ required: true, message: '请选择阈值字段' }]}
                      >
                        <Select placeholder="选择阈值字段">
                          {businessModels
                            .find(model => model.id === sensingForm.getFieldValue('model_id'))?.fields
                            ?.map((field) => (
                              <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                            )) || []}
                        </Select>
                      </Form.Item>
                    );
                  }
                  return null;
                }}
              </Form.Item>
              <Form.Item name="operator" label="操作符" initialValue="gt">
                <Select>
                  <Option value="gt">大于</Option>
                  <Option value="lt">小于</Option>
                  <Option value="eq">等于</Option>
                  <Option value="ne">不等于</Option>
                  <Option value="gte">大于等于</Option>
                  <Option value="lte">小于等于</Option>
                </Select>
              </Form.Item>
              <Form.Item name="check_interval" label="检查间隔 (秒)" initialValue={5}>
                <Input type="number" min={1} max={60} />
              </Form.Item>
            </div>
          )}
          
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 驱动逻辑配置编辑/新增模态框 */}
      <Modal
        title={editingDriveLogic ? '编辑驱动逻辑配置' : '添加驱动逻辑配置'}
        open={driveLogicModalVisible}
        onOk={() => driveLogicForm.submit()}
        onCancel={() => setDriveLogicModalVisible(false)}
        width={600}
        afterOpenChange={(open) => {
          if (open && editingDriveLogic) {
            setSelectedDriveLogicType(editingDriveLogic.type || 'first_order');
          }
        }}
      >
        <Form 
          form={driveLogicForm} 
          layout="vertical" 
          onFinish={handleSaveDriveLogic}
          onValuesChange={(changedValues) => {
            if (changedValues.type) {
              setSelectedDriveLogicType(changedValues.type);
            }
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：温度告警驱动逻辑" />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select placeholder="选择驱动逻辑类型">
              <Option value="first_order">
                <div>
                  <div><strong>一阶函数</strong></div>
                  <div style={{ fontSize: '12px', color: '#888' }}>简单的条件判断逻辑</div>
                </div>
              </Option>
              <Option value="script">
                <div>
                  <div><strong>脚本函数</strong></div>
                  <div style={{ fontSize: '12px', color: '#888' }}>使用Python脚本处理复杂逻辑</div>
                </div>
              </Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="event_temp_ids" label="关联数据感知事件">
            <Select mode="multiple" placeholder="选择触发此逻辑的数据感知事件">
              {configs.sensing_configs.map(config => (
                <Option key={config.temp_id} value={config.temp_id}>
                  {config.name} ({config.type === 'data_change' ? '数据变化' : '阈值触发'})
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item name="action_ids" label="关联行动">
            <Select mode="multiple" placeholder="选择触发后要执行的行动">
              {actions.map(action => (
                <Option key={action.id} value={action.id}>
                  {action.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          {/* 一阶函数可选预处理配置 */}
          {selectedDriveLogicType === 'first_order' && (
            <Card size="small" title="预处理配置 (可选)" style={{ marginBottom: 16 }}>
              <Form.Item name="pre_condition" label="前置条件">
                <Input.TextArea 
                  rows={2} 
                  placeholder="可选的前置处理条件表达式" 
                />
              </Form.Item>
            </Card>
          )}
          
          {/* 脚本函数可选预处理配置 */}
          {selectedDriveLogicType === 'script' && (
            <Card size="small" title="预处理脚本 (可选)" style={{ marginBottom: 16 }}>
              <Form.Item name="script_content" label="脚本内容">
                <Input.TextArea 
                  rows={4} 
                  placeholder="可选的预处理脚本，用于对事件数据进行处理" 
                />
              </Form.Item>
            </Card>
          )}
          
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="描述此驱动逻辑的作用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentImport;