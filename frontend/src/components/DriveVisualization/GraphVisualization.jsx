import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const GraphVisualization = ({ data, onNodeClick }) => {
  const svgRef = useRef();

  // 处理窗口大小变化
  const handleResize = () => {
    if (svgRef.current && data && data.nodes && data.edges) {
      const container = svgRef.current.parentElement;
      const newWidth = container ? container.clientWidth : 1200;
      
      // 更新SVG尺寸
      d3.select(svgRef.current)
        .attr('width', newWidth);
      
      // 重新计算力导向布局的中心点
      const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.edges).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(newWidth / 2, 400))
        .force('collision', d3.forceCollide().radius(60));
      
      // 重启模拟
      simulation.alpha(1).restart();
    }
  };

  useEffect(() => {
    if (!data || !data.nodes || !data.edges) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // 获取父容器的宽度，确保图形占满可用空间
    const container = svgRef.current.parentElement;
    const width = container ? container.clientWidth : 1200;
    const height = 800;

    // 添加窗口大小变化监听器
    window.addEventListener('resize', handleResize);

    // 创建缩放行为
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    const g = svg.append('g');

    // 创建力导向布局
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60));

    // 创建连线
    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // 创建节点组
    const node = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .enter()
      .append('g')
      .call(drag(simulation));

    // 添加节点圆圈
    const circle = node.append('circle')
      .attr('r', 25)
      .attr('fill', d => getNodeColor(d.type))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('click', (event, d) => {
        event.stopPropagation();
        onNodeClick(d);
      });

    // 添加tooltip功能 - 直接添加到body以避免定位问题
    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'graph-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '8px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '10000'); // 确保在最上层

    // 鼠标悬停事件
    circle.on('mouseenter', function(event, d) {
      tooltip.transition()
        .duration(200)
        .style('opacity', 0.9);
      
      let tooltipContent = `<strong>${d.name}</strong><br/>`;
      tooltipContent += `<em>类型: ${getTypeDisplayName(d.type)}</em><br/>`;
      
      if (d.description) {
        tooltipContent += `<div style="margin-top: 4px;">${d.description}</div>`;
      }
      
      // 根据节点类型显示特定信息
      switch(d.type) {
        case 'data_source':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            数据源ID: ${d.data.id}<br/>
            类型: ${d.data.type}
          </div>`;
          break;
        case 'business_model':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            模型ID: ${d.data.id}<br/>
            字段数量: ${d.data.field_count}
          </div>`;
          break;
        case 'sensing_config':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            配置ID: ${d.data.id}<br/>
            类型: ${d.data.type}<br/>
            状态: ${d.data.status ? '激活' : '停用'}
          </div>`;
          break;
        case 'drive_logic':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            逻辑ID: ${d.data.id}<br/>
            类型: ${d.data.type}
          </div>`;
          break;
        case 'task':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            任务ID: ${d.data.id}
          </div>`;
          break;
        case 'capability':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            能力ID: ${d.data.id}
          </div>`;
          break;
        case 'agent':
          tooltipContent += `<div style="margin-top: 4px; font-size: 11px;">
            Agent ID: ${d.data.id}<br/>
            状态: ${d.data.status}
          </div>`;
          break;
      }
      
      // 直接使用节点元素的getBoundingClientRect获取页面绝对位置
      const circleElement = this;
      const circleRect = circleElement.getBoundingClientRect();
      
      // 计算tooltip位置（在节点右上方）
      const tooltipX = circleRect.left + circleRect.width + 10;
      const tooltipY = circleRect.top - 10;
      
      tooltip.html(tooltipContent)
        .style('left', tooltipX + 'px')
        .style('top', tooltipY + 'px');
    })
    .on('mouseleave', () => {
      tooltip.transition()
        .duration(200)
        .style('opacity', 0);
    });

    // 添加节点文本
    const text = node.append('text')
      .attr('dy', 5)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#000')
      .text(d => d.name.length > 8 ? d.name.substring(0, 8) + '...' : d.name);

    // 为文本元素添加相同的事件处理
    text.on('mouseenter', function(event, d) {
        // 触发父节点的mouseenter事件
        d3.select(this.parentNode).select('circle').dispatch('mouseenter', { detail: d });
      })
      .on('mouseleave', function() {
        // 触发父节点的mouseleave事件  
        d3.select(this.parentNode).select('circle').dispatch('mouseleave');
      });

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    });

    // 拖拽函数
    function drag(simulation) {
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
    }

    // 节点颜色映射
    function getNodeColor(nodeType) {
      const colorMap = {
        'data_source': '#4CAF50',
        'business_model': '#2196F3',
        'sensing_config': '#FF9800',
        'drive_logic': '#9C27B0',
        'task': '#E91E63',
        'capability': '#607D8B',
        'agent': '#795548'
      };
      return colorMap[nodeType] || '#9E9E9E';
    }

    // 节点类型显示名称映射
    function getTypeDisplayName(nodeType) {
      const typeMap = {
        'data_source': '数据源',
        'business_model': '业务模型',
        'sensing_config': '数据感知配置',
        'drive_logic': '驱动逻辑',
        'task': '任务',
        'capability': '能力',
        'agent': 'Agent'
      };
      return typeMap[nodeType] || nodeType;
    }

    // 清理函数
    return () => {
      simulation.stop();
      window.removeEventListener('resize', handleResize);
      // 清理tooltip
      d3.select('body').select('.graph-tooltip').remove();
    };
  }, [data, onNodeClick]);

  return (
    <div style={{ overflow: 'hidden', border: '1px solid #e8e8e8', borderRadius: 4, width: '100%' }}>
      <svg ref={svgRef} width="100%" height="800"></svg>
    </div>
  );
};

export default GraphVisualization;