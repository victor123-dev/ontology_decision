// 供应链控制塔 - 预警详情抽屉组件
// 包含：基本信息 + 根因分析 + 建议行动（自动执行/人工处理）
import { useState } from "react";
import { X, AlertTriangle, CheckCircle, Clock, Play, User, ArrowRight, Loader2 } from "lucide-react";
import { getRiskTextColor, getStatusColor, alertDashboardApi } from "../lib/data";

export default function AlertDrawer({ alert, onClose, onStatusChange, onRefresh }) { const [activeTab, setActiveTab] = useState('info');
  const [autoExecState, setAutoExecState] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [manualProcessing, setManualProcessing] = useState(false);

  if (!alert) return null;

  const handleAutoExec = () => { if (autoExecState !== 'idle') return;
    setAutoExecState('running');
    setProgress(0);
    const steps = [0, 15, 32, 48, 65, 78, 90, 100];
    let i = 0;
    const interval = setInterval(() => { if (i < steps.length) { setProgress(steps[i]);
        i++; } else { clearInterval(interval);
        setAutoExecState('done');
        onStatusChange(alert.id, '已处理');
        onRefresh && onRefresh(); } }, 400); };

  const handleManualProcess = async () => {
    if (manualProcessing) return;
    setManualProcessing(true);
    try {
      await alertDashboardApi.processAlertManual(alert.id);
      onStatusChange(alert.id, '已处理');
      onRefresh && onRefresh();
      onClose();
    } catch (e) {
      console.error('人工处理失败:', e);
      alert('处理失败: ' + e.message);
    } finally {
      setManualProcessing(false);
    }
  };

  const riskColor = getRiskTextColor(alert.riskLevel);
  const statusColor = getStatusColor(alert.status);

  return (
    <>
      {/* 遮罩 */}
      <div
        style={{ position: 'fixed', inset: 0, zIndex: 40,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />

      {/* 抽屉 */}
      <div
        style={{ position: 'fixed', right: 0, top: 0, height: '100%', zIndex: 50,
          display: 'flex', flexDirection: 'column', width: '520px',
          background: 'linear-gradient(180deg, #0f1d35 0%, #0b1426 100%)',
          borderLeft: '1px solid rgba(59,130,246,0.25)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.6)' }}
      >
        {/* 标题栏 */}
        <div
          style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
            padding: '16px 24px', flexShrink: 0,
            borderBottom: '1px solid rgba(59,130,246,0.15)' }}
        >
          <div style={{ flex: 1, paddingRight: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '9999px',
                  fontWeight: 500,
                  background: `${riskColor}20`, color: riskColor,
                  border: `1px solid ${riskColor}40` }}
              >
                {alert.riskLevel}
              </span>
              <span
                style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '9999px',
                  fontWeight: 500,
                  background: `${statusColor}20`, color: statusColor,
                  border: `1px solid ${statusColor}40` }}
              >
                {alert.status}
              </span>
            </div>
            <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', lineHeight: '1.4' }}>
              {alert.title}
            </h2>
            <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
              {alert.createdAt} · 规则编码: {alert.ruleCode}
            </p>
          </div>
          <button onClick={onClose}
            style={{ color: '#94a3b8', cursor: 'pointer', flexShrink: 0, marginTop: '4px',
              background: 'transparent', border: 'none', transition: 'color 0.2s' }}
            onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
            onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}>
            <X size={18} />
          </button>
        </div>

        {/* Tab切换 */}
        <div style={{ display: 'flex', padding: '12px 24px 0', gap: '4px', flexShrink: 0 }}>
          {(['info', 'action']).map((tab, idx) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{ padding: '6px 14px', fontSize: '13px',
                borderRadius: idx === 0 ? '6px 0 0 0' : idx === 1 ? '0 6px 0 0' : '0',
                transition: 'all 0.2s', cursor: 'pointer',
                ...(activeTab === tab
                  ? { background: 'rgba(59,130,246,0.2)', color: '#60a5fa',
                      border: '1px solid rgba(59,130,246,0.4)', borderBottom: 'none' }
                  : { color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(255,255,255,0.05)' }) }}
              onMouseOver={e => {
                if (activeTab !== tab) {
                  e.currentTarget.style.color = '#e2e8f0';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                }
              }}
              onMouseOut={e => {
                if (activeTab !== tab) {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                }
              }}
            >
              {tab === 'info' ? '基本信息' : '建议行动'}
            </button>
          ))}
        </div>

        {/* 内容区 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 24px',
          scrollbarWidth: 'thin', scrollbarColor: 'rgba(59,130,246,0.3) transparent' }}>
          {activeTab === 'info' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingTop: '16px' }}>
              {/* 消息内容 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                  消息内容
                </h3>
                <p style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.7' }}>
                  {alert.content}
                </p>
              </div>

              {/* 关联信息 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                  关联信息
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                  {[
                    { label: '关联采购订单', value: alert.poId },
                    { label: '供应商', value: alert.supplier },
                    { label: '关联销售订单', value: alert.soId },
                    { label: '客户', value: alert.customer },
                  ].map(item => (
                    <div key={item.label}>
                      <span style={{ fontSize: '12px', color: '#64748b' }}>{item.label}</span>
                      <p style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 500, marginTop: '4px' }}>
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* 根因分析 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px',
                  display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={12} style={{ color: '#fbbf24' }} />
                  根因分析
                </h3>
                <pre style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.7',
                  whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                  {alert.rootCause}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'action' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingTop: '16px' }}>
              {/* 建议行动描述 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                  建议行动描述
                </h3>
                <p style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.7' }}>
                  {alert.action.description}
                </p>
              </div>

              {/* 行动流程 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                <h3 style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8',
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px' }}>
                  行动流程
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {alert.action.steps.map((step, idx) => (
                    <div key={step.id} style={{ display: 'flex', gap: '12px' }}>
                      {/* 步骤编号 */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                        <div
                          style={{ width: '28px', height: '28px', borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '12px', fontWeight: 'bold', flexShrink: 0,
                            ...(step.type === 'end'
                              ? { background: 'rgba(34,197,94,0.2)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.4)' }
                              : step.type === 'decision'
                              ? { background: 'rgba(245,158,11,0.2)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.4)' }
                              : { background: 'rgba(59,130,246,0.2)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.4)' }) }}
                        >
                          {step.type === 'end' ? <CheckCircle size={14} /> : step.id}
                        </div>
                        {idx < alert.action.steps.length - 1 && (
                          <div style={{ width: '2px', flex: 1, marginTop: '4px',
                            background: 'rgba(59,130,246,0.2)', minHeight: '12px' }} />
                        )}
                      </div>

                      {/* 步骤内容 */}
                      <div style={{ flex: 1, paddingBottom: '12px' }}>
                        <p style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 500 }}>{step.step}</p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                          <span style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <User size={10} /> {step.role}
                          </span>
                          <span style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={10} /> {step.deadline}
                          </span>
                        </div>
                        <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>输出：{step.output}</p>

                        {/* 决策分支 */}
                        {step.branches && (
                          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                            {step.branches.map(branch => (
                              <div
                                key={branch.label}
                                style={{ display: 'flex', alignItems: 'center', gap: '4px',
                                  fontSize: '12px', padding: '4px 8px', borderRadius: '4px',
                                  background: 'rgba(245,158,11,0.1)', color: '#f59e0b',
                                  border: '1px solid rgba(245,158,11,0.2)' }}
                              >
                                <ArrowRight size={10} />
                                {branch.label} → {branch.nextStep}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 执行按钮区 */}
              <div style={{
                background: '#0f1d35', borderRadius: '8px',
                border: '1px solid rgba(59,130,246,0.12)',
                padding: '16px'
              }}>
                {alert.status === '已处理' || autoExecState === 'done' ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                    gap: '8px', padding: '8px 0' }}>
                    <CheckCircle size={16} style={{ color: '#4ade80' }} />
                    <span style={{ fontSize: '14px', color: '#4ade80', fontWeight: 500 }}>已处理</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {autoExecState === 'running' && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between',
                          fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                          <span>自动执行中...</span>
                          <span>{progress}%</span>
                        </div>
                        <div style={{ height: '8px', borderRadius: '9999px', overflow: 'hidden',
                          background: 'rgba(59,130,246,0.15)' }}>
                          <div
                            style={{ height: '100%', borderRadius: '9999px', transition: 'all 0.3s',
                              width: `${progress}%`, background: 'linear-gradient(90deg, #3b82f6, #06b6d4)' }}
                          />
                        </div>
                        <p style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
                          正在按照建议行动流程执行处理脚本...
                        </p>
                      </div>
                    )}
                    {autoExecState === 'idle' && (
                      <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                          onClick={handleAutoExec}
                          style={{ flex: 1, display: 'flex', alignItems: 'center',
                            justifyContent: 'center', gap: '8px',
                            padding: '10px 0', borderRadius: '8px',
                            fontSize: '14px', fontWeight: 500, cursor: 'pointer',
                            transition: 'all 0.2s',
                            background: 'linear-gradient(135deg, #1e3a5f, #1e40af)',
                            color: '#93c5fd', border: '1px solid rgba(59,130,246,0.4)' }}
                          onMouseOver={e => e.currentTarget.style.opacity = '0.9'}
                          onMouseOut={e => e.currentTarget.style.opacity = '1'}
                        >
                          <Play size={14} />
                          自动执行
                        </button>
                        <button
                          onClick={handleManualProcess}
                          disabled={manualProcessing}
                          style={{ flex: 1, display: 'flex', alignItems: 'center',
                            justifyContent: 'center', gap: '8px',
                            padding: '10px 0', borderRadius: '8px',
                            fontSize: '14px', fontWeight: 500, cursor: manualProcessing ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s',
                            background: manualProcessing ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.06)',
                            color: manualProcessing ? '#64748b' : '#94a3b8',
                            border: '1px solid rgba(255,255,255,0.12)' }}
                          onMouseOver={e => { if (!manualProcessing) e.currentTarget.style.opacity = '0.9'; }}
                          onMouseOut={e => e.currentTarget.style.opacity = '1'}
                        >
                          {manualProcessing ? (
                            <>
                              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                              处理中...
                            </>
                          ) : (
                            <>
                              <User size={14} />
                              人工处理
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  ); }
