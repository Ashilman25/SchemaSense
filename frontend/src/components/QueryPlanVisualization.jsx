import { useCallback, useMemo, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position
} from "reactflow";
import "reactflow/dist/style.css";
import {useTheme} from '../context/ThemeContext'

const CustomNode = ({data}) => {
  const {theme} = useTheme();

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-md min-w-[200px] ${
        theme === 'dark' ? 'bg-slate-800 border-blue-500 text-white' : 'bg-white border-blue-600 text-gray-900'
      }`}
    >
      <Handle type = "target" position = {Position.Top} />

      <div className = "font-semibold text-sm mb-2">{data.type}</div>
      {data.table && (
        <div className={`text-xs mb-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
          Table: <span className = "font-medium">{data.table}</span>
        </div>

      )}
      
      <div className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
        <div>Rows: <span className = "font-medium">{data.rows}</span></div>
        <div>Cost: <span className = "font-medium">{data.cost.toFixed(2)}</span></div>
      </div>

      <Handle type = "source" position = {Position.Bottom} />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};


const QueryPlanVisualization = ({planData}) => {
  const {theme} = useTheme();

  //plan -> react flow format
  const {initialNodes, initialEdges} = useMemo(() => {
    if (!planData || !planData.nodes) {
      return {initialNodes: [], initialEdges: []}
    };

    //map to track node pos
    const nodeMap = new Map();
    planData.nodes.forEach((node) => {
      nodeMap.set(node.id, node);
    });

    //make layout using tree
    const levelMap = new Map(); 
    const childrenMap = new Map(); 

    //build children map
    planData.edges.forEach((edge) => {
      if (!childrenMap.has(edge.to)) {
        childrenMap.set(edge.to, []);
      }
      
      childrenMap.get(edge.to).push(edge.from);
    });

    //find root
    const rootNodes = planData.nodes.filter((node) => {
      return !planData.edges.some((edge) => edge.from === node.id);
    });

    //BFS to assign levels
    const queue = rootNodes.map((node) => ({id: node.id, level: 0}));
    while (queue.length > 0) {
      const {id, level} = queue.shift();

      if (!levelMap.has(level)) {
        levelMap.set(level, []);
      }

      levelMap.get(level).push(id);

      const children = childrenMap.get(id) || [];
      children.forEach((childId) => {
        queue.push({id: childId, level: level + 1});
      });
    }

    //positions
    const nodeWidth = 220;
    const nodeHeight = 100;
    const horizontalSpacing = 50;
    const verticalSpacing = 100;

    const nodes = planData.nodes.map((node) => {
      let level = 0;
      let indexInLevel = 0;

      for (const [lvl, nodeIds] of levelMap.entries()) {
        const idx = nodeIds.indexOf(node.id);

        if (idx !== -1) {
          level = lvl;
          indexInLevel = idx;
          break;
        }
      }

      const nodesInLevel = levelMap.get(level)?.length || 1;
      const totalWidth = nodesInLevel * nodeWidth + (nodesInLevel - 1) * horizontalSpacing;

      const x = indexInLevel * (nodeWidth + horizontalSpacing) - totalWidth / 2 + 400;
      const y = level * (nodeHeight + verticalSpacing) + 50;

      return {
        id: node.id,
        type: 'custom',
        position: {x, y},
        data: {
          type: node.type,
          table: node.table,
          rows: node.rows,
          cost: node.cost,
        },
      };
    });

    const edges = planData.edges.map((edge, index) => ({
      id: `e-${edge.from}-${edge.to}-${index}`,
      source: edge.from,
      target: edge.to,
      type: 'smoothstep',
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 20,
        height: 20,
        color: theme === 'dark' ? '#60a5fa' : '#2563eb',
      },
      style : {
        stroke: theme === 'dark' ? '#60a5fa' : '#2563eb',
        strokeWidth: 2,
      },
    }));

    return {initialNodes: nodes, initialEdges: edges};

  }, [planData, theme]);








};

export default QueryPlanVisualization;