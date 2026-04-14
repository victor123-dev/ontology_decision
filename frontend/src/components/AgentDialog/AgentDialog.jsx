import { useEffect, useState } from 'react';

const AgentPanel = ({ visible, onClose }) => {
  const [iframeLoaded, setIframeLoaded] = useState(false);
  
  useEffect(() => {
    if (visible) {
      // 重置加载状态
      setIframeLoaded(false);
    }
  }, [visible]);
  
  const handleIframeLoad = () => {
    setIframeLoaded(true);
  };
  
  if (!visible) {
    return null;
  }
  
  return (
    <div className={`agent-panel ${!visible ? 'hidden' : ''}`}>
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
      <button 
        className="agent-panel-close" 
        onClick={onClose}
        aria-label="关闭面板"
      >
        ×
      </button>
    </div>
  );
};

export default AgentPanel;