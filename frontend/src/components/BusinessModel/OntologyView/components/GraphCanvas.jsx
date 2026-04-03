import React from 'react';
import { useD3ForceGraph } from '../hooks/useD3ForceGraph';

const GraphCanvas = ({ data, onSelect, selectedId }) => {
  const { svgRef } = useD3ForceGraph(data, onSelect, selectedId);

  return (
    <svg 
      ref={svgRef} 
      style={{ 
        width: '100%', 
        height: '100%', 
        backgroundColor: '#F8FAFC',
        backgroundImage: 'radial-gradient(#CBD5E1 1px, transparent 0)',
        backgroundSize: '20px 20px'
      }}
    />
  );
};

export default GraphCanvas;