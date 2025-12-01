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