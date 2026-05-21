import AlertDashboard from './components/AlertDashboard/AlertDashboard'

function EmbedDashboard() {
  return (
    <div style={{ 
      width: '100vw', 
      minHeight: '100vh', 
      overflow: 'auto'
    }}>
      <AlertDashboard hideHeader={true} />
    </div>
  )
}

export default EmbedDashboard
