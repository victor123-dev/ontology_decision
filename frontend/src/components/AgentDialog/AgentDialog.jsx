import { useEffect, useState } from 'react';
import { FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons';

const AgentPanel = ({ visible, onClose }) => {
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  useEffect(() => {
    if (visible) {
      // 重置加载状态
      setIframeLoaded(false);
    }
  }, [visible]);
  
  const handleIframeLoad = () => {
    setIframeLoaded(true);
  };
  
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };
  
  // 全屏时禁用主应用滚动，退出时恢复
  useEffect(() => {
    if (!isFullscreen) return;
    
    const scrollY = window.scrollY;
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.body.style.overflow = '';
      window.scrollTo(0, scrollY);
    };
  }, [isFullscreen]);
  
  // 关闭面板时自动退出全屏
  useEffect(() => {
    if (!visible) {
      setIsFullscreen(false);
    }
  }, [visible]);
  
  if (!visible) {
    return null;
  }
  
  return (
    <div className={`agent-panel ${!visible ? 'hidden' : ''} ${isFullscreen ? 'fullscreen' : ''}`}>
      {!iframeLoaded && (
        <div className="agent-loading-spinner">
          <div className="spinner"></div>
          <span>加载 Agent 对话界面...</span>
        </div>
      )}
      <iframe
        src="http://localhost:3000/workspace"
        className={`agent-iframe ${iframeLoaded ? 'loaded' : ''}`}
        onLoad={handleIframeLoad}
        title="DeerFlow Agent"
      />
      <div className="agent-panel-actions">
        <button 
          className="agent-panel-action-btn" 
          onClick={toggleFullscreen}
          aria-label={isFullscreen ? '退出全屏' : '全屏'}
          title={isFullscreen ? '退出全屏' : '全屏'}
        >
          {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
        </button>
        <button 
          className="agent-panel-close" 
          onClick={onClose}
          aria-label="关闭面板"
          title="关闭面板"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default AgentPanel;