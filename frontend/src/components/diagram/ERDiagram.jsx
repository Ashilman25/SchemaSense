import {useState, useCallback, useEffect} from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import TableNode from './TableNode';

const nodeTypes = {
    tableNode: TableNode,
};

const ERDiagram = ({schema}) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [nodePositions, setNodePositions] = useState({});
    const [expandNodes, setExpandedNodes] = useState({});

    const handleToggleExpand = useCallback((nodeId) => {
        setExpandedNodes(prev => ({
            ...prev,
            [nodeId]: !prev[nodeId],
        }));
    }, []);

    //schema into react flow nodes
    const createNodesFromSchema = useCallback((schemaData, positions = {}, expanded = {}) => {
        if (!schemaData || !schemaData.tables) return [];

        const tableNodes = schemaData.tables.map((table, index) => {
            const tableKey = `${table.schema}.${table.name}`;

            let position;
            if (positions[tableKey]) {
                position = positions[tableKey];

            } else {
                //default to 3 col grid layout
                const col = index % 3;
                const row = Math.floor(index / 3);

                position = {
                    x: col * 350 + 50,
                    y: row * 250 + 50,
                };
            }

            return {
                id: tableKey,
                type: 'tableNode',
                position,
                data: {
                    tableName: table.name,
                    schema: table.schema,
                    columns: table.columns,
                    isExpanded: expanded[tableKey] || false,
                    onToggleExpand: handleToggleExpand,
                    nodeId: tableKey,
                },
            };
        });

        return tableNodes;
    }, [handleToggleExpand]);








};

export default ERDiagram;

