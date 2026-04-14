const AgentButton = ({ onClick, isVisible = true }) => {
  if (!isVisible) return null;
  
  return (
    <div 
      onClick={onClick}
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 50,
        width: '56px',
        height: '56px',
        borderRadius: '50%',
        boxShadow: 'rgba(59, 130, 246, 0.4) 0px 0px 20px, rgba(0, 0, 0, 0.5) 0px 4px 16px',
        transition: 'transform 0.2s',
        overflow: 'hidden',
        cursor: 'pointer',
        transform: 'scale(1)'
      }}
    >
      <img 
        src="https://d2xsxph8kpxj0f.cloudfront.net/310519663439243238/eAaE9FZQc3rqCtqMQX6MhY/ai-assistant-avatar-J5Q2yuSctb9uAPyCaaRM3z.webp" 
        alt="AI Assistant" 
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
    </div>
  );
};

export default AgentButton;