// 供应链控制塔 - AI供应链助手组件
// 悬浮图标 + 对话框 + 可贴边隐藏
import { useState, useRef, useEffect } from "react";
import { X, Send, Minimize2, ChevronRight } from "lucide-react";
import { kpiData, alertMessages } from "../lib/data";

const AI_AVATAR = "https://d2xsxph8kpxj0f.cloudfront.net/310519663439243238/eAaE9FZQc3rqCtqMQX6MhY/ai-assistant-avatar-J5Q2yuSctb9uAPyCaaRM3z.webp";

// 预设问答
const quickQuestions = [
  '当前有哪些高风险预警？',
  '本月采购到货及时率如何？',
  '哪个供应商风险最高？',
  '分析缺料根因',
];

function generateAIResponse(question) { const q = question.toLowerCase();
  if (q.includes('高风险') || q.includes('预警')) { const highRisk = alertMessages.filter(m => m.riskLevel === '最高风险' || m.riskLevel === '高风险');
    return `当前共有 **${highRisk.length}** 条高风险及以上预警：\n\n${highRisk.map((m, i) => `${i+1}. **${m.riskLevel}** - ${m.title.substring(0, 30)}...`).join('\n')}\n\n建议优先处理「ArF光刻胶供应中断」和「FPGA出口管制」两项最高风险预警，这两项直接影响生产连续性。`; }
  if (q.includes('及时率') || q.includes('到货')) { return `本月采购到货及时率为 **${kpiData.purchaseOnTimeRate}%**，较上月下降 2.1 个百分点。\n\n主要拖累因素：\n1. 德国默克半导体材料 OTD 76%（下滑趋势）\n2. 日本东京电子 TEL OTD 78%（地震影响）\n3. 美国赛灵思 Xilinx 出口管制风险\n\n建议：对默克和 TEL 启动供应商绩效改善计划（SIP），同时评估备用供应商。`; }
  if (q.includes('供应商') && q.includes('风险')) { return `当前供应商风险排名：\n\n🔴 **最高风险**\n- 美国赛灵思 Xilinx：出口管制风险，FPGA供应面临中断\n- 日本信越化学工业：ArF光刻胶交期延误7天\n\n🟠 **高风险**\n- 韩国SK海力士：LPDDR4交期延误，影响工单WO000045\n\n🟡 **中风险**\n- 德国默克半导体：OTD连续3月下滑至76%\n- 日本东京电子TEL：OTD下滑至78%（地震影响）`; }
  if (q.includes('缺料') || q.includes('根因')) { return `**缺料根因分析摘要**\n\n当前缺料问题主要集中在以下3个维度：\n\n**1. 需求预测偏差（占比40%）**\nQ2订单量超预期+35%，导致安全库存设置不足，MRP计划滞后。\n\n**2. 供应商产能不足（占比35%）**\n信越化学设备故障、TEL地震停产、SK海力士产能紧张，多家关键供应商同期出现问题。\n\n**3. 地缘政治风险（占比25%）**\nFPGA出口管制为新增风险，影响深远，需启动国产替代战略。\n\n**建议行动**：启动供应链韧性提升项目，重点推进多供应商策略和国产替代评估。`; }
  if (q.includes('销售') || q.includes('订单金额')) { return `本月销售数据概览：\n\n- **销售订单金额**：¥${kpiData.monthlySalesAmount.toFixed(2)} 万元\n- **销售订单数量**：${kpiData.monthlySalesQty.toFixed(0)} 单\n- **预警消息数**：${kpiData.alertCount} 条\n\n主要客户：华为海思半导体、中芯国际、三星电子、长江存储\n\n当前有 2 张销售订单（SO000015、SO000018）面临交期风险，建议优先处理对应的供应链预警。`; }
  return `感谢您的提问！关于「${question}」，我正在分析供应链数据...\n\n根据当前数据，本月关键指标：\n- 采购到货及时率：${kpiData.purchaseOnTimeRate}%\n- 当月销售金额：¥${kpiData.monthlySalesAmount}万\n- 活跃预警：${kpiData.alertCount}条\n- 自动执行：${kpiData.autoExecCount}次\n\n如需深入分析，请告诉我具体关注的维度（供应商/物料/客户/工单）。`; }

export default function AiAssistant() { const [isOpen, setIsOpen] = useState(false);
  const [isHidden, setIsHidden] = useState(false);
  const [messages, setMessages] = useState([
    { id: '0',
      role: 'assistant',
      content: '您好！我是供应链助手 🤖\n\n我可以帮您：\n- **问数查询**：查询KPI、库存、订单数据\n- **数据分析**：分析供应链风险和趋势\n- **报告生成**：生成供应链分析报告\n- **预警根因**：解读预警消息和根因分析\n\n请问有什么可以帮您？',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = (text) => { if (!text.trim()) return;
    const userMsg = { id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => { const aiMsg = { id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateAIResponse(text),
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) };
      setMessages(prev => [...prev, aiMsg]);
      setIsTyping(false); }, 1200); };

  if (isHidden) { return (
      <button
        onClick={() => setIsHidden(false)}
        style={{ position: 'fixed', right: 0, top: '50%', transform: 'translateY(-50%)',
          zIndex: 50, display: 'flex', alignItems: 'center', gap: '4px',
          padding: '16px 4px', borderRadius: '8px 0 0 8px',
          fontSize: '12px', color: '#fff',
          background: 'linear-gradient(180deg, #1e3a5f, #0f1d35)',
          border: '1px solid rgba(59,130,246,0.3)', borderRight: 'none',
          cursor: 'pointer' }}
        title="展开供应链助手"
      >
        <ChevronRight size={14} />
        <span style={{ writingMode: 'vertical-rl', textOrientation: 'mixed',
          fontSize: '10px', color: '#94a3b8' }}>助手</span>
      </button>
    ); }

  return (
    <>
      {/* 悬浮按钮 */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 50,
            width: '56px', height: '56px', borderRadius: '50%',
            boxShadow: '0 0 20px rgba(59,130,246,0.4), 0 4px 16px rgba(0,0,0,0.5)',
            transition: 'transform 0.2s', overflow: 'hidden', cursor: 'pointer' }}
          onMouseOver={e => e.currentTarget.style.transform = 'scale(1.1)'}
          onMouseOut={e => e.currentTarget.style.transform = 'scale(1)'}
          title="供应链助手"
        >
          <img src={AI_AVATAR} alt="AI助手" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          {/* 未读提示 */}
          <div style={{ position: 'absolute', top: 0, right: 0,
            width: '16px', height: '16px', borderRadius: '50%',
            background: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#fff', fontSize: '9px', fontWeight: 'bold' }}>1</span>
          </div>
        </button>
      )}

      {/* 对话框 */}
      {isOpen && (
        <div
          style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 50,
            width: '384px', display: 'flex', flexDirection: 'column',
            borderRadius: '12px', overflow: 'hidden',
            height: 'min(1000px, calc(100vh - 80px))',
            background: 'linear-gradient(180deg, #0f1d35 0%, #0b1426 100%)',
            border: '1px solid rgba(59,130,246,0.3)',
            boxShadow: '0 0 30px rgba(59,130,246,0.2), 0 8px 32px rgba(0,0,0,0.6)' }}
        >
          {/* 标题栏 */}
          <div
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', flexShrink: 0,
              background: 'linear-gradient(90deg, rgba(59,130,246,0.15), rgba(6,182,212,0.1))',
              borderBottom: '1px solid rgba(59,130,246,0.2)' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', overflow: 'hidden' }}>
                <img src={AI_AVATAR} alt="AI" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9' }}>供应链助手</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%',
                    background: '#4ade80', animation: 'pulse 2s ease-out infinite' }} />
                  <span style={{ fontSize: '12px', color: '#94a3b8' }}>在线</span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button onClick={() => setIsHidden(true)}
                style={{ color: '#94a3b8', cursor: 'pointer', padding: '4px',
                  background: 'transparent', border: 'none', transition: 'color 0.2s' }}
                onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
                onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}>
                <Minimize2 size={14} />
              </button>
              <button onClick={() => setIsOpen(false)}
                style={{ color: '#94a3b8', cursor: 'pointer', padding: '4px',
                  background: 'transparent', border: 'none', transition: 'color 0.2s' }}
                onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
                onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}>
                <X size={14} />
              </button>
            </div>
          </div>

          {/* 消息区 */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px',
            display: 'flex', flexDirection: 'column', gap: '12px',
            scrollbarWidth: 'thin', scrollbarColor: 'rgba(59,130,246,0.3) transparent' }}>
            {messages.map(msg => (
              <div key={msg.id} style={{ display: 'flex', gap: '8px',
                ...(msg.role === 'user' ? { flexDirection: 'row-reverse' } : {}) }}>
                {msg.role === 'assistant' && (
                  <div style={{ width: '28px', height: '28px', borderRadius: '50%',
                    overflow: 'hidden', flexShrink: 0 }}>
                    <img src={AI_AVATAR} alt="AI" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </div>
                )}
                <div style={{ maxWidth: '80%',
                  ...(msg.role === 'user' ? { alignItems: 'flex-end' } : { alignItems: 'flex-start' }),
                  display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div
                    style={{ padding: '8px 12px', borderRadius: '12px', fontSize: '14px',
                      lineHeight: '1.6', whiteSpace: 'pre-line',
                      ...(msg.role === 'user'
                        ? { background: 'rgba(59,130,246,0.25)', color: '#e2e8f0',
                            borderRadius: '12px 4px 12px 12px' }
                        : { background: 'rgba(255,255,255,0.06)', color: '#e2e8f0',
                            borderRadius: '4px 12px 12px 12px',
                            border: '1px solid rgba(255,255,255,0.08)' }) }}
                    dangerouslySetInnerHTML={{ __html: msg.content
                        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#60a5fa">$1</strong>')
                        .replace(/\n/g, '<br/>') }}
                  />
                  <span style={{ fontSize: '10px', color: '#64748b' }}>{msg.timestamp}</span>
                </div>
              </div>
            ))}
            {isTyping && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%',
                  overflow: 'hidden', flexShrink: 0 }}>
                  <img src={AI_AVATAR} alt="AI" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
                <div style={{ padding: '8px 12px', borderRadius: '12px',
                  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '16px' }}>
                    {[0, 1, 2].map(i => (
                      <div key={i} style={{ width: '6px', height: '6px', borderRadius: '50%',
                        background: '#60a5fa', animation: 'bounce 1s infinite',
                        animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷问题 */}
          <div style={{ padding: '8px 16px', display: 'flex', gap: '8px',
            overflowX: 'auto', flexShrink: 0, scrollbarWidth: 'none' }}>
            {quickQuestions.map(q => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                style={{ flexShrink: 0, fontSize: '12px', padding: '4px 10px',
                  borderRadius: '9999px', cursor: 'pointer', transition: 'opacity 0.2s',
                  background: 'rgba(59,130,246,0.15)', color: '#93c5fd',
                  border: '1px solid rgba(59,130,246,0.25)' }}
                onMouseOver={e => e.currentTarget.style.opacity = '0.8'}
                onMouseOut={e => e.currentTarget.style.opacity = '1'}
              >
                {q}
              </button>
            ))}
          </div>

          {/* 输入框 */}
          <div style={{ padding: '0 16px 16px', flexShrink: 0 }}>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px',
                borderRadius: '8px', padding: '8px 12px',
                background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(59,130,246,0.25)' }}
            >
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
                placeholder="询问供应链数据或分析..."
                style={{ flex: 1, background: 'transparent', fontSize: '14px',
                  color: '#e2e8f0', outline: 'none', border: 'none' }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim()}
                style={{ width: '28px', height: '28px', borderRadius: '6px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s', cursor: 'pointer',
                  background: input.trim() ? '#3b82f6' : 'rgba(59,130,246,0.2)',
                  opacity: input.trim() ? 1 : 0.4 }}
              >
                <Send size={13} style={{ color: '#fff' }} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  ); }
