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
import TableDetailPanel from './TableDetailPanel';
import AddTableModal from '../modals/AddTableModal';
import RenameTableModal from '../modals/RenameTableModal';
import TableContextMenu from './TableContextMenu';
import {schemaAPI} from '../../utils/api';

const nodeTypes = {
    tableNode: TableNode,
};

const ERDiagram = ({schema, onAskAboutTable, onSchemaUpdate, isDbConnected}) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [nodePositions, setNodePositions] = useState({});
    const [expandedNodes, setExpandedNodes] = useState({});
    const [selectedNode, setSelectedNode] = useState(null);
    const [showAddTableModal, setShowAddTableModal] = useState(false);
    const [showRenameTableModal, setShowRenameTableModal] = useState(false);
    const [contextMenu, setContextMenu] = useState(null);
    const [tableToRename, setTableToRename] = useState(null);

    const handleToggleExpand = useCallback((nodeId) => {
        setExpandedNodes(prev => ({
            ...prev,
            [nodeId]: !prev[nodeId],
        }));
    }, []);

    const handleNodeClick = useCallback((nodeId) => {
        setSelectedNode(nodeId);
    }, []);

    const handleCloseDetailPanel = useCallback(() => {
        setSelectedNode(null);
    }, []);

    const handleTableContextMenu = useCallback((event, nodeId) => {
        event.preventDefault();
        setContextMenu({
            x: event.clientX,
            y: event.clientY,
            nodeId
        });

    }, []);

    const handleAddTable = async (tableData) => {
        try {
            const actions = [
                {
                    type: 'add_table',
                    name: tableData.tableName,
                    schema: tableData.schema
                }
            ];

            for (const col of tableData.columns) {
                actions.push({
                    type: 'add_column',
                    table: `${tableData.schema}.${tableData.tableName}`,
                    column: col
                });
            }

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to add table');
            }

        } catch (error) {
            console.error('Failed to add table:', error);
            throw error;
        }
    };

    const handleRenameTable = async (newName) => {
        if (!tableToRename) return;

        try {
            const [schema, oldName] = tableToRename.split('.');

            const actions = [{
                type: 'rename_table',
                old_name: oldName,
                new_name: newName,
                schema: schema
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);
                setSelectedNode(null);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to rename table');
            }

        } catch (error) {
            console.error('Failed to rename table:', error);
            throw error;
        }
    };

    const handleDeleteTable = async (tableKey) => {
        try {
            const [schema, name] = tableKey.split('.');

            const actions = [{
                type: 'drop_table',
                name: name,
                schema: schema,
                force: false
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);
                setSelectedNode(null);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to delete table');
            }

        } catch (error) {
            console.error('Failed to delete table:', error);
            alert(`Failed to delete table: ${error.message}`);
        }
    };

    //schema into nodes
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
                    onNodeClick: handleNodeClick,
                    onContextMenu: handleTableContextMenu,
                },
                selected: false,
            };
        });

        return tableNodes;
    }, [handleToggleExpand, handleNodeClick, handleTableContextMenu]);


    //schema FK relations into edges
    const createEdgesFromSchema = useCallback((schemaData) => {
        if (!schemaData || !schemaData.relationships) return [];

        const relationshipEdges = schemaData.relationships.map((rel, index) => {
            const sourceKey = rel.from_table;
            const targetKey = rel.to_table;

            return {
                id: `edge-${index}`,
                source: sourceKey,
                target: targetKey,
                type: 'smoothstep',
                animated: false,
                style: {stroke: '#3b82f6', strokeWidth: 2},
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: '#3b82f6',
                },
                label: `${rel.from_column} → ${rel.to_column}`,
                labelStyle: {fill: '#6b7280', fontSize: 10},
                labelBgStyle: {fill: '#ffffff', fillOpacity: 0.8},
            };
        });

        return relationshipEdges;
    }, []);

    //if schema changes, initial nodes and edges
    useEffect(() => {
        if (schema) {
            const newNodes = createNodesFromSchema(schema, nodePositions, expandedNodes);
            const newEdges = createEdgesFromSchema(schema);

            setNodes(newNodes);
            setEdges(newEdges);
        }
    }, [schema, createNodesFromSchema, createEdgesFromSchema, setNodes, setEdges, nodePositions, expandedNodes]);

    //if selected node changes, update
    useEffect(() => {
        setNodes((nds) =>
            nds.map((node) => ({
                ...node,
                selected: node.id === selectedNode,
            }))
        );

        //edge highlighting
        if (selectedNode) {
            setEdges((eds) =>
                eds.map((edge) => {
                    const isConnected = edge.source === selectedNode || edge.target === selectedNode;
                    return {
                        ...edge,
                        animated: isConnected,
                        style: {
                            ...edge.style,
                            stroke: isConnected ? '#10b981' : '#3b82f6',
                            strokeWidth: isConnected ? 3 : 2,
                        },
                    };
                })
            );
        } else {
            //reset to default style if none selected
            setEdges((eds) =>
                eds.map((edge) => ({
                    ...edge,
                    animated: false,
                    style: { stroke: '#3b82f6', strokeWidth: 2 },
                }))
            );
        }
    }, [selectedNode, setNodes, setEdges]);

    //drag dropped
    const onNodeDragStop = useCallback((_event, node) => {
        setNodePositions(prev => ({
            ...prev,
            [node.id]: node.position,
        }));
    }, []);

    //minimap color
    const nodeColor = () => {
        return '#3b82f6';
    }

    // Show "Connect to database" message ONLY if not connected
    // If connected but empty, show the empty ER diagram canvas with Add Table button
    if (!isDbConnected) {
        return (
            <div className = "h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                <div className = "text-center">
                    <svg className = "w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>

                    <p className = "text-sm font-medium">No database connected</p>
                    <p className = "text-xs mt-2">Connect to a database to view the ER diagram</p>
                </div>
            </div>
        );
    }

    // Get selected table details
    const selectedTable = selectedNode && schema?.tables ? schema.tables.find(t => `${t.schema}.${t.name}` === selectedNode) : null;

    return (
        <div className = "h-full w-full relative">

            {/* add table */}
            <button
                onClick = {() => setShowAddTableModal(true)}
                className = "absolute top-4 right-4 z-10 bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg transition-colors flex items-center space-x-2"
            >
                <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 4v16m8-8H4" />
                </svg>

                <span>Add Table</span>
            </button>

            <ReactFlow 
                nodes = {nodes}
                edges = {edges}
                onNodesChange = {onNodesChange}
                onEdgesChange = {onEdgesChange}
                onNodeDragStop = {onNodeDragStop}
                nodeTypes = {nodeTypes}
                fitView
                fitViewOptions = {{
                    padding: 0.2,
                    includeHiddenNodes: false,
                }}
                minZoom = {0.1}
                maxZoom = {2}
                defaultEdgeOptions = {{
                    type: 'smoothstep',
                }}
            >
                <Background 
                    variant = "dots"
                    gap = {16}
                    size = {1}
                    color = "#94a3b8"
                    className = "dark:opacity-30"
                />

                <Controls showInteractive = {false} className = "bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg shadow-lg" />

                <MiniMap 
                    style = {{width: 120, height: 80}} //default 200x150
                    nodeColor = {nodeColor}
                    nodeStrokeWidth = {3}
                    zoomable
                    pannable
                    className = "bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg shadow-lg"
                />

            </ReactFlow>

            {/* Table detail panel */}
            {selectedNode && selectedTable && (
                <TableDetailPanel
                    table = {selectedTable}
                    schema = {schema}
                    onClose = {handleCloseDetailPanel}
                    onAskAboutTable = {onAskAboutTable}
                    onSchemaUpdate = {onSchemaUpdate}
                />
            )}


            <AddTableModal
                isOpen = {showAddTableModal}
                onClose = {() => setShowAddTableModal(false)}
                onSubmit = {handleAddTable}
            />

            <RenameTableModal
                isOpen = {showRenameTableModal}
                onClose = {() => {
                    setShowRenameTableModal(false);
                    setTableToRename(null);
                }}
                onSubmit = {handleRenameTable}
                currentName = {tableToRename ? tableToRename.split('.')[1] : ''}
            />


            {contextMenu && (
                <TableContextMenu
                    position = {{x: contextMenu.x, y: contextMenu.y}}
                    onClose = {() => setContextMenu(null)}
                    onRename = {() => {
                        setTableToRename(contextMenu.nodeId);
                        setShowRenameTableModal(true);
                    }}
                    onDelete = {() => handleDeleteTable(contextMenu.nodeId)}
                    tableName = {contextMenu.nodeId ? contextMenu.nodeId.split('.')[1] : ''}
                />
            )}
        </div>
    );
};

export default ERDiagram;

