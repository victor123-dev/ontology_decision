const Solver = () => {
  return (
    <div style={{ 
      width: '100%', 
      height: '100vh',
      margin: 0,
      padding: 0,
      overflow: 'hidden'
    }}>
      <iframe
        src="http://localhost:3030/logic-orchestration/69fd5d854500a17b2742e4d2"
        style={{ 
          width: '100%', 
          height: '100%', 
          border: 'none',
          margin: 0,
          padding: 0
        }}
        title="求解器"
      />
    </div>
  )
}

export default Solver
