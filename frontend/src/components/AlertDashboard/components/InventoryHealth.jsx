import { useEffect, useState } from 'react';
import { useLowInventoryAlerts } from '../hooks/useOperationData';
import { calculateInventoryHealth, getInventoryHealthColor } from '../lib/operationUtils';
import { message, Modal, Spin, Select, Button, InputNumber } from 'antd';
import { ShoppingOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;

export default function InventoryHealth({ refreshTrigger }) {
  const { data: alerts, loading, error, refetch } = useLowInventoryAlerts();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [recommendedSuppliers, setRecommendedSuppliers] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [purchaseQuantity, setPurchaseQuantity] = useState(0);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
    }
  }, [refreshTrigger, refetch]);

  // 打开紧急采购对话框
  const handleEmergencyPurchase = async (material) => {
    setSelectedMaterial(material);
    setIsModalVisible(true);
    setLoadingSuppliers(true);
    setSelectedSupplier(null);
    
    try {
      // 调用推荐供应商 API
      const response = await axios.post('/api/v1/alert-dashboard/inventory/recommend-suppliers', null, {
        params: {
          material_id: material.material_id,
          urgency_level: 'high'
        }
      });
      
      if (response.data.success) {
        const result = response.data.result;
        setRecommendedSuppliers(result.recommended_suppliers || []);
        setPurchaseQuantity(result.recommended_quantity || 0);
        
        // 默认选择第一个供应商
        if (result.recommended_suppliers && result.recommended_suppliers.length > 0) {
          setSelectedSupplier(result.recommended_suppliers[0]);
        }
      } else {
        message.error(response.data.error || '获取推荐供应商失败');
        setRecommendedSuppliers([]);
      }
    } catch (err) {
      message.error('获取推荐供应商失败: ' + err.message);
      setRecommendedSuppliers([]);
    } finally {
      setLoadingSuppliers(false);
    }
  };
  
  // 确认采购
  const handleConfirmPurchase = async () => {
    if (!selectedSupplier) {
      message.warning('请选择供应商');
      return;
    }
    
    if (!purchaseQuantity || purchaseQuantity <= 0) {
      message.warning('请输入有效的采购数量');
      return;
    }
    
    setPurchasing(true);
    
    try {
      const response = await axios.post('/api/v1/alert-dashboard/inventory/emergency-purchase', {
        material_id: selectedMaterial.material_id,
        quantity: purchaseQuantity,
        supplier_id: selectedSupplier.supplier_id,
        urgency_level: 'high',
        reason: `库存低于安全库存，当前可用: ${selectedMaterial.available_quantity}, 安全库存: ${selectedMaterial.safety_stock_level}`
      });
      
      if (response.data.success) {
        const result = response.data.result;
        message.success(`紧急采购订单创建成功！订单号: ${result.po_id}`);
        setIsModalVisible(false);
        refetch(); // 刷新库存列表
      } else {
        message.error(response.data.error || '创建采购订单失败');
      }
    } catch (err) {
      message.error('创建采购订单失败: ' + err.message);
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <div style={{
          width: '32px', height: '32px',
          border: '3px solid rgba(59,130,246,0.2)',
          borderTop: '3px solid #3b82f6',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
      </div>
    );
  }

  if (error) {
    return <div style={{ padding: '16px', color: '#ef4444', fontSize: '12px' }}>加载失败: {error}</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: '8px', fontSize: '11px', color: '#8aa3c0' }}>
        共 {alerts.length} 个物料低于安全库存
      </div>
      
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.15)' }}>
              <th style={{ padding: '6px', textAlign: 'left', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>物料</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>可用</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>已采未到</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>安全</th>
              <th style={{ padding: '6px', textAlign: 'center', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>健康度</th>
              <th style={{ padding: '6px', textAlign: 'center', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>建议行动</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(item => {
              const healthRatio = calculateInventoryHealth(item.available_quantity, item.safety_stock_level);
              const healthColor = getInventoryHealthColor(healthRatio);
              
              // 使用调整后的健康度（包含在途加分）
              const adjustedHealthRatio = item.adjusted_health_ratio || healthRatio;
              const adjustedHealthColor = getInventoryHealthColor(adjustedHealthRatio);
              
              return (
                <tr key={item.inventory_id} style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                  <td style={{ padding: '6px' }}>
                    <div style={{ color: '#2c5282', fontSize: '11px' }}>{item.material_name}</div>
                    <div style={{ color: '#8aa3c0', fontSize: '9px' }}>{item.material_id}</div>
                  </td>
                  <td style={{ padding: '6px', textAlign: 'right', color: healthColor, fontWeight: 'bold' }}>
                    {item.available_quantity.toFixed(0)}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>
                    {item.in_transit_quantity > 0 ? (
                      <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>
                        {item.in_transit_quantity.toFixed(0)}
                      </span>
                    ) : (
                      <span style={{ color: '#8aa3c0' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'right', color: '#6b8cae' }}>
                    {item.safety_stock_level.toFixed(0)}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                      <div style={{ width: '40px', height: '4px', background: 'rgba(0,0,0,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${Math.min(adjustedHealthRatio, 100)}%`,
                            background: adjustedHealthColor,
                            borderRadius: '2px'
                          }}
                        />
                      </div>
                      <span style={{ color: adjustedHealthColor, fontSize: '10px', minWidth: '35px' }}>
                        {adjustedHealthRatio.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    {adjustedHealthRatio > 70 ? (
                      <span style={{ color: '#8aa3c0' }}>-</span>
                    ) : (
                      <Button
                        type="primary"
                        size="small"
                        icon={<ShoppingOutlined />}
                        onClick={() => handleEmergencyPurchase(item)}
                        style={{
                          fontSize: '10px',
                          height: '22px',
                          padding: '0 8px',
                          background: '#ef4444',
                          border: 'none'
                        }}
                      >
                        紧急采购
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
            
            {alerts.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: '32px', textAlign: 'center', color: '#8aa3c0' }}>
                  ✓ 所有物料库存充足
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* 紧急采购对话框 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShoppingOutlined style={{ color: '#ef4444' }} />
            <span>紧急采购</span>
          </div>
        }
        open={isModalVisible}
        onOk={handleConfirmPurchase}
        onCancel={() => setIsModalVisible(false)}
        confirmLoading={purchasing}
        okText="确认采购"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        {loadingSuppliers ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px', color: '#8aa3c0' }}>正在获取推荐供应商...</div>
          </div>
        ) : selectedMaterial && (
          <div style={{ padding: '16px 0' }}>
            {/* 物料信息 */}
            <div style={{ marginBottom: '24px', padding: '16px', background: '#f0f7ff', borderRadius: '8px' }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#2c5282', marginBottom: '8px' }}>
                {selectedMaterial.material_name}
              </div>
              <div style={{ fontSize: '12px', color: '#6b8cae', marginBottom: '4px' }}>
                物料ID: {selectedMaterial.material_id}
              </div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
                <div>
                  <div style={{ fontSize: '11px', color: '#8aa3c0' }}>当前可用</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#ef4444' }}>
                    {selectedMaterial.available_quantity.toFixed(0)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#8aa3c0' }}>已采未到</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#3b82f6' }}>
                    {selectedMaterial.in_transit_quantity > 0 ? selectedMaterial.in_transit_quantity.toFixed(0) : '-'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#8aa3c0' }}>安全库存</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#10b981' }}>
                    {selectedMaterial.safety_stock_level.toFixed(0)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: '#8aa3c0' }}>缺口</div>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#f59e0b' }}>
                    {Math.max(0, selectedMaterial.safety_stock_level - selectedMaterial.available_quantity).toFixed(0)}
                  </div>
                </div>
              </div>
            </div>
            
            {/* 采购数量 */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: '#6b8cae', marginBottom: '8px' }}>采购数量</div>
              <InputNumber
                value={purchaseQuantity}
                onChange={setPurchaseQuantity}
                min={0}
                precision={0}
                style={{ width: '100%' }}
                size="large"
              />
            </div>
            
            {/* 推荐供应商 */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: '#6b8cae', marginBottom: '8px' }}>推荐供应商</div>
              <Select
                value={selectedSupplier?.supplier_id}
                onChange={(value) => {
                  const supplier = recommendedSuppliers.find(s => s.supplier_id === value);
                  setSelectedSupplier(supplier);
                }}
                style={{ width: '100%' }}
                size="large"
              >
                {recommendedSuppliers.map(supplier => (
                  <Option key={supplier.supplier_id} value={supplier.supplier_id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{supplier.supplier_name}</span>
                      <span style={{ color: '#10b981', fontSize: '11px' }}>
                        评分: {supplier.scores.total_score}
                      </span>
                    </div>
                  </Option>
                ))}
              </Select>
            </div>
            
            {/* 选中供应商详情 */}
            {selectedSupplier && (
              <div style={{ padding: '12px', background: '#f0f7ff', borderRadius: '6px', fontSize: '12px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <span style={{ color: '#8aa3c0' }}>单价: </span>
                    <span style={{ color: '#2c5282' }}>¥{selectedSupplier.unit_price}</span>
                  </div>
                  <div>
                    <span style={{ color: '#8aa3c0' }}>交期: </span>
                    <span style={{ color: '#2c5282' }}>{selectedSupplier.lead_time_days}天</span>
                  </div>
                  <div>
                    <span style={{ color: '#8aa3c0' }}>预计金额: </span>
                    <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>
                      ¥{(purchaseQuantity * selectedSupplier.unit_price).toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#8aa3c0' }}>预计到货: </span>
                    <span style={{ color: '#2c5282' }}>{selectedSupplier.expected_delivery_date}</span>
                  </div>
                </div>
              </div>
            )}
            
            {recommendedSuppliers.length === 0 && !loadingSuppliers && (
              <div style={{ textAlign: 'center', padding: '20px', color: '#8aa3c0' }}>
                没有找到可用供应商
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
