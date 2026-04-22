import { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';

const GRAPH_CONFIG = {
  NODE_RADIUS: 24,
  LINK_DISTANCE: 180,
  MIN_ZOOM: 0.1,
  MAX_ZOOM: 4,
  DEFAULT_STROKE: '#CBD5E1',
  SELECTED_STROKE: '#FF4D4F',
  NODE_DEFAULT_FILL: '#FFFFFF',
  NODE_SELECTED_FILL: '#EFF6FF',
  NODE_STROKE: '#2563EB',
  ACTION_NODE_FILL: '#FFF7ED',
  ACTION_NODE_STROKE: '#EA580C',
  LABEL_FONT_SIZE: 12,
  HIGHLIGHTED_NODE_FILL: '#F0F9FF',
  HIGHLIGHTED_NODE_STROKE: '#003097ff',
};

// 需要高亮的模型ID列表
const HIGHLIGHTED_MODEL_IDS = new Set([
  'supplier',
  'inventory', 
  'purchase_order',
  'order_detail',
  'requisition',
  'procurement_plan',
  'mrp_demand',
  'production_plan',
  'work_order',
  'material_detail',
  'sales_order',
  'customer',
  'bom_child',
  'bom_parent'
]);

export const useD3ForceGraph = (data, onSelect, selectedId) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const elementsRef = useRef({ links: null, nodes: null, linkGroup: null, nodeGroup: null, linkLabelGroup: null });

  // 1. 初始化画布 (只在 data 变化时执行)
  useEffect(() => {
    if (!svgRef.current || !data || !data.nodes || !data.links) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;

    svg.selectAll("*").remove();
    const g = svg.append("g");

    svg.append("defs").append("marker")
      .attr("id", "arrowhead-static")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", GRAPH_CONFIG.NODE_RADIUS + 10)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M 0,-5 L 10,0 L 0,5")
      .attr("fill", GRAPH_CONFIG.DEFAULT_STROKE);

    const zoom = d3.zoom()
      .scaleExtent([GRAPH_CONFIG.MIN_ZOOM, GRAPH_CONFIG.MAX_ZOOM])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    svg.call(zoom);

    // 注意层级顺序：Links -> LinkLabels -> Nodes
    const linkGroup = g.append("g").attr("class", "links");
    const linkLabelGroup = g.append("g").attr("class", "link-labels");
    const nodeGroup = g.append("g").attr("class", "nodes");

    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(GRAPH_CONFIG.LINK_DISTANCE))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(GRAPH_CONFIG.NODE_RADIUS * 2));

    simulationRef.current = simulation;
    elementsRef.current = { linkGroup, nodeGroup, linkLabelGroup };

    // --- 开始渲染 ---

    // 1. 渲染边
    const links = linkGroup.selectAll("line")
      .data(data.links, d => d.id);

    links.enter().append("line")
      .attr("stroke", GRAPH_CONFIG.DEFAULT_STROKE)
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrowhead-static)")
      .attr("cursor", (d) => d.data?.type === 'action_to_model' ? 'default' : 'pointer')
      .on("click", (event, d) => {
        event.stopPropagation();
        // 行动相关的边不可选中
        if (d.data?.type === 'action_to_model') {
          return;
        }
        // 还原原始链接对象，保持 source 和 target 为字符串 ID
        const originalLink = {
          id: d.id,
          source: d.source?.id || d.source,  // 如果是对象就取 id，否则保持原值
          target: d.target?.id || d.target,  // 如果是对象就取 id，否则保持原值
          name: d.name,
          description: d.description,
          data: d.data
        };
        onSelect({ type: 'link', data: originalLink });
      })
      .merge(links);

    links.exit().remove();

    // 2. 渲染边标签
    const labelGroups = linkLabelGroup.selectAll("g")
      .data(data.links, d => d.id);

    const labelEnter = labelGroups.enter().append("g").attr("class", "link-label-container");
    
    // 标签背景
    labelEnter.append("rect")
      .attr("fill", "#FFFFFF")
      .attr("rx", 4)
      .attr("ry", 4);
    
    // 标签文字
    labelEnter.append("text")
      .attr("font-size", "12px")
      .attr("fill", "#475569")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .text(d => d.name);

    labelGroups.exit().remove();

    // 3. 渲染节点
    const nodeGroups = nodeGroup.selectAll("g")
      .data(data.nodes, d => d.id);

    const nodeEnter = nodeGroups.enter().append("g")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    nodeEnter.append("circle")
      .attr("r", GRAPH_CONFIG.NODE_RADIUS)
      .attr("fill", d => {
        if (d.type === 'action') {
          return GRAPH_CONFIG.ACTION_NODE_FILL;
        }
        if (HIGHLIGHTED_MODEL_IDS.has(d.id)) {
          return GRAPH_CONFIG.HIGHLIGHTED_NODE_FILL;
        }
        return GRAPH_CONFIG.NODE_DEFAULT_FILL;
      })
      .attr("stroke", d => {
        if (d.type === 'action') {
          return GRAPH_CONFIG.ACTION_NODE_STROKE;
        }
        if (HIGHLIGHTED_MODEL_IDS.has(d.id)) {
          return GRAPH_CONFIG.HIGHLIGHTED_NODE_STROKE;
        }
        return GRAPH_CONFIG.NODE_STROKE;
      })
      .attr("stroke-width", 2);

    nodeEnter.append("text")
      .attr("dy", GRAPH_CONFIG.NODE_RADIUS + 20)
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .text(d => d.name);

    nodeEnter.on("click", (event, d) => {
      event.stopPropagation();
      // 还原原始节点对象，排除 D3 添加的 x/y/fx/fy 等属性
      const originalNode = {
        id: d.id,
        name: d.name,
        type: d.type,
        description: d.description,
        data: d.data
      };
      onSelect({ type: d.type === 'action' ? 'action' : 'business_model', data: originalNode });
    });

    nodeGroups.exit().remove();

    // 4. Tick 更新 (核心动画循环)
    simulation.on("tick", () => {
      // 更新边位置
      linkGroup.selectAll("line")
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      // 更新边标签位置
      linkLabelGroup.selectAll("g")
        .attr("transform", d => `translate(${(d.source.x + d.target.x) / 2}, ${(d.source.y + d.target.y) / 2})`)
        .each(function() {
          const text = d3.select(this).select("text");
          const bbox = text.node()?.getBBox();
          if (bbox) {
            d3.select(this).select("rect")
              .attr("x", bbox.x - 4)
              .attr("y", bbox.y - 2)
              .attr("width", bbox.width + 8)
              .attr("height", bbox.height + 4);
          }
        });

      // 更新节点位置
      nodeGroup.selectAll("g")
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    svg.on("click", () => onSelect(null));

    return () => {
      if (simulationRef.current) simulationRef.current.stop();
    };
  }, [data]);

  // 2. 单独的 Effect：只处理选中样式更新
  useEffect(() => {
    if (!elementsRef.current.linkGroup || !elementsRef.current.nodeGroup) return;

    const { linkGroup, nodeGroup } = elementsRef.current;

    // 更新边的样式
    linkGroup.selectAll("line")
      .attr("stroke", d => d.id === selectedId ? GRAPH_CONFIG.SELECTED_STROKE : GRAPH_CONFIG.DEFAULT_STROKE)
      .attr("stroke-width", d => d.id === selectedId ? 4 : 2);

    // 更新节点的样式
    nodeGroup.selectAll("g").select("circle")
      .attr("fill", d => {
        if (d.id === selectedId) {
          return GRAPH_CONFIG.NODE_SELECTED_FILL;
        }
        if (d.type === 'action') {
          return GRAPH_CONFIG.ACTION_NODE_FILL;
        }
        if (HIGHLIGHTED_MODEL_IDS.has(d.id)) {
          return GRAPH_CONFIG.HIGHLIGHTED_NODE_FILL;
        }
        return GRAPH_CONFIG.NODE_DEFAULT_FILL;
      })
      .attr("stroke", d => {
        if (d.id === selectedId) {
          return GRAPH_CONFIG.SELECTED_STROKE;
        }
        if (d.type === 'action') {
          return GRAPH_CONFIG.ACTION_NODE_STROKE;
        }
        if (HIGHLIGHTED_MODEL_IDS.has(d.id)) {
          return GRAPH_CONFIG.HIGHLIGHTED_NODE_STROKE;
        }
        return GRAPH_CONFIG.NODE_STROKE;
      })
      .attr("stroke-width", d => d.id === selectedId ? 4 : 2);

  }, [selectedId]);

  return { svgRef };
};