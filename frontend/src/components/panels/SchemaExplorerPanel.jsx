import {useState, useEffect, useCallback} from "react";
import { schemaAPI } from "../../utils/api";
import ERDiagram from "../diagram/ERDiagram";

const SchemaExplorerPanel = ({ onAskAboutTable, isDbConnected, refreshTrigger, onSchemaChange, onRegisterUpdateCallback }) => {
    const [activeTab, setActiveTab] = useState('tables')
    const [schema, setSchema] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedTables, setExpandedTables] = useState(new Set());

    const [searchTerm, setSearchTerm] = useState('');
    const [notification, setNotification] = useState(null);

    const MAX_HISTORY_SIZE = 10;
    const [undoStack, setUndoStack] = useState([]);
    const [redoStack, setRedoStack] = useState([]);
    const [currentDdl, setCurrentDdl] = useState(null);
    const [isUndoRedoInProgress, setIsUndoRedoInProgress] = useState(false);

    useEffect(() => {
        if (isDbConnected) {
            fetchSchema();

        } else {
            setSchema(null);
            setError(null);
        }

    }, [isDbConnected, refreshTrigger]);


    useEffect(() => {
        if (schema && onSchemaChange) {
            onSchemaChange(schema, currentDdl);
        }
    }, [schema, currentDdl, onSchemaChange]); 

    const handleSchemaUpdate = useCallback((newSchema, newDDL) => {
        setUndoStack(prevStack => {
            if (schema && currentDdl) {
                const snapshot = {
                    schema: JSON.parse(JSON.stringify(schema)),
                    ddl: currentDdl
                };

                const newStack = [...prevStack, snapshot];

                if (newStack.length > MAX_HISTORY_SIZE) {
                    newStack.shift();
                }

                return newStack;
            }
            return prevStack;
        });

        setRedoStack([]);
        setSchema(newSchema);
        setCurrentDdl(newDDL);

        setNotification({
            type: 'success',
            message: 'Changes saved to virtual schema (not applied to DB)'
        });

        setTimeout(() => {
            setNotification(null);
        }, 5000);
    }, [schema, currentDdl]);

    useEffect(() => {
        if (onRegisterUpdateCallback) {
            onRegisterUpdateCallback(handleSchemaUpdate);
        }
    }, [handleSchemaUpdate, onRegisterUpdateCallback]);

    const handleUndo = useCallback(async () => {
        if (undoStack.length === 0 || isUndoRedoInProgress) return;

        const previousSnapshot = undoStack[undoStack.length - 1];

        setIsUndoRedoInProgress(true);

        try {
            await schemaAPI.applyDDLEdit(previousSnapshot.ddl);

            setUndoStack(prevStack => prevStack.slice(0, -1));
            setRedoStack(prevStack => {
                const snapshot = {
                    schema: JSON.parse(JSON.stringify(schema)),
                    ddl: currentDdl
                };

                const newStack = [...prevStack, snapshot];

                if (newStack.length > MAX_HISTORY_SIZE) {
                    newStack.shift();
                }

                return newStack;
            });

            const restoredSchema = JSON.parse(JSON.stringify(previousSnapshot.schema));
            setSchema(restoredSchema);
            setCurrentDdl(previousSnapshot.ddl);

            setNotification({
                type: 'success',
                message: 'Undo successful'
            });

            setTimeout(() => {
                setNotification(null);
            }, 3000);

        } catch (err) {
            console.error('Undo failed:', err);
            setNotification({
                type: 'error',
                message: `Undo failed: ${err.message || 'Unknown error'}`
            });

            setTimeout(() => {
                setNotification(null);
            }, 5000);

        } finally {
            setIsUndoRedoInProgress(false);
        }

    }, [undoStack, schema, currentDdl, isUndoRedoInProgress]);

    const handleRedo = useCallback(async () => {
        if (redoStack.length === 0 || isUndoRedoInProgress) return;

        const nextSnapshot = redoStack[redoStack.length - 1];

        setIsUndoRedoInProgress(true);

        try {
            await schemaAPI.applyDDLEdit(nextSnapshot.ddl);

            setRedoStack(prevStack => prevStack.slice(0, -1));
            setUndoStack(prevStack => {
                const snapshot = {
                    schema: JSON.parse(JSON.stringify(schema)),
                    ddl: currentDdl
                };

                const newStack = [...prevStack, snapshot];

                if (newStack.length > MAX_HISTORY_SIZE) {
                    newStack.shift();
                }

                return newStack;
            });

            const restoredSchema = JSON.parse(JSON.stringify(nextSnapshot.schema));
            setSchema(restoredSchema);
            setCurrentDdl(nextSnapshot.ddl);

            setNotification({
                type: 'success',
                message: 'Redo successful'
            });

            setTimeout(() => {
                setNotification(null);
            }, 3000);

        } catch (err) {
            console.error('Redo failed:', err);
            setNotification({
                type: 'error',
                message: `Redo failed: ${err.message || 'Unknown error'}`
            });

            setTimeout(() => {
                setNotification(null);
            }, 5000);

        } finally {
            setIsUndoRedoInProgress(false);
        }

    }, [redoStack, schema, currentDdl, isUndoRedoInProgress]);

    const fetchSchema = async () => {
        setLoading(true);
        setError(null);

        try {
            const [schemaData, ddlData] = await Promise.all([
                schemaAPI.getSchema(),
                schemaAPI.getDDL()
            ]);

            setSchema(schemaData);
            setCurrentDdl(ddlData.ddl);
            setUndoStack([]);
            setRedoStack([]);

        } catch (err) {
            console.error('Failed to fetch schema:', err);
            setError(err.message || 'Failed to load schema');

        } finally {
            setLoading(false);
        }
    };

    const toggleTable = (tableKey) => {
        const newExpanded = new Set(expandedTables);

        if (newExpanded.has(tableKey)) {
            newExpanded.delete(tableKey);

        } else {
            newExpanded.add(tableKey);
        }

        setExpandedTables(newExpanded);
    };


    const getFilteredTables = () => {
        if (!schema || !schema.tables) return [];

        return schema.tables.filter(table => {

            if (searchTerm) {
                const search = searchTerm.toLowerCase();
                const tableName = table.name.toLowerCase();
                const schemaName = table.schema.toLowerCase();
                const fullName = `${schemaName}.${tableName}`;

                return tableName.includes(search) ||
                       schemaName.includes(search) ||
                       fullName.includes(search);
            }

            return true;
        });
    };

    const getFilteredSchema = () => {
        if (!schema) return null;

        const filteredTables = getFilteredTables();
        const filteredTableKeys = new Set(
            filteredTables.map(t => `${t.schema}.${t.name}`)
        );


        const filteredRelationships = schema.relationships?.filter(rel =>
            filteredTableKeys.has(rel.from_table) && filteredTableKeys.has(rel.to_table)
        ) || [];

        return {
            tables: filteredTables,
            relationships: filteredRelationships
        };
    };

    const renderTablesList = () => {
        if (!isDbConnected) {
            return (
                <div className = "flex flex-col items-center justify-center py-8 px-4 text-center">
                    <svg className = "w-12 h-12 text-gray-400 dark:text-gray-500 mb-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                    <p className = "text-sm text-gray-600 dark:text-gray-400 mb-2">
                        No database connected
                    </p>
                    <p className = "text-xs text-gray-500 dark:text-gray-500">
                        Click the settings icon in the top right to connect to a database
                    </p>
                </div>
            );
        }

        if (loading) {
            return (
                <div className = "flex items-center justify-center py-8">
                    <div className = "text-sm text-gray-500 dark:text-gray-400">Loading schema...</div>
                </div>
            );
        }

        if (error) {
            return (
                <div className = "text-sm text-red-600 dark:text-red-400 p-3 bg-red-50 dark:bg-red-900/20 rounded">
                    {error}
                </div>
            );
        }

        if (!schema || !schema.tables || schema.tables.length === 0) {
            return (
                <div className = "text-sm text-gray-500 dark:text-gray-400">
                    No tables found in this database
                </div>
            );
        }

        const filteredTables = getFilteredTables();

        if (filteredTables.length === 0) {
            return (
                <div className = "text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                    {searchTerm ? (
                        <>
                            <svg className = "w-10 h-10 mx-auto mb-2 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            No tables match &quot;{searchTerm}&quot;
                        </>
                    ) : (
                        'No tables to display'
                    )}
                </div>
            );
        }

        return (
            <div className = "space-y-2">
                {filteredTables.map((table) => {
                    const tableKey = `${table.schema}.${table.name}`;
                    const isExpanded = expandedTables.has(tableKey);

                    return (
                        <div
                            key = {tableKey}
                            className = "border border-gray-200 dark:border-slate-600 rounded-lg overflow-hidden"
                        >
                            {/* Table header */}
                            <div className = "w-full px-3 py-2 bg-gray-50 dark:bg-slate-700/50 flex items-center justify-between">
                                <button onClick={() => toggleTable(tableKey)} className = "flex items-center space-x-2 flex-1 hover:bg-gray-100 dark:hover:bg-slate-700 -mx-3 -my-2 px-3 py-2 transition-colors">
                                    <svg
                                        className = {`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                                        fill = "none"
                                        stroke = "currentColor"
                                        viewBox = "0 0 24 24"
                                    >
                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M9 5l7 7-7 7" />
                                    </svg>

                                    <span className = "text-sm font-medium text-gray-700 dark:text-gray-300">
                                        {table.name}
                                    </span>

                                    <span className = "text-xs text-gray-500 dark:text-gray-400">
                                        ({table.schema})
                                    </span>

                                    <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                                        {table.columns.length} column{table.columns.length !== 1 ? 's' : ''}
                                    </span>
                                </button>

                                {/* Ask about this table button */}
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onAskAboutTable(tableKey);
                                    }}
                                    className = "ml-2 text-xs bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-800/50 text-blue-700 dark:text-blue-300 px-2 py-1 rounded transition-colors flex items-center space-x-1"
                                    title="Ask about this table"
                                >
                                    <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span>Ask</span>
                                </button>
                            </div>

                            {/* Columns list */}
                            {isExpanded && (
                                <div className = "bg-white dark:bg-slate-800">
                                    <div className = "px-3 py-2 space-y-1">
                                        {table.columns.map((column, idx) => (
                                            <div key = {idx} className = "flex items-center justify-between py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-slate-700/50 rounded transition-colors">
                                                <div className = "flex items-center space-x-2 flex-1">
                                                    <span className = "text-sm text-gray-700 dark:text-gray-300 font-mono">
                                                        {column.name}
                                                    </span>

                                                    <div className = "flex items-center space-x-1">
                                                        {column.is_pk && (
                                                            <span className = "text-xs px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded font-medium" title ="Primary Key">
                                                                PK
                                                            </span>
                                                        )}
                                                        {column.is_fk && (
                                                            <span className = "text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-medium" title = "Foreign Key">
                                                                FK
                                                            </span>
                                                        )}
                                                    </div>

                                                </div>

                                                <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                                    {column.type}
                                                </span>

                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div className = "h-full bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-gray-200 dark:border-slate-700 flex flex-col transition-colors relative">

            {/* notification banner */}
            {notification && (
                <div className = {`absolute top-0 left-0 right-0 z-20 px-4 py-3 ${
                    notification.type === 'success'
                        ? 'bg-green-100 dark:bg-green-900/30 border-b border-green-200 dark:border-green-800'
                        : 'bg-red-100 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800'
                }`}>
                    <div className = "flex items-center justify-between">
                        <div className = "flex items-center space-x-2">
                            {notification.type === 'success' ? (
                                <svg className = "w-5 h-5 text-green-600 dark:text-green-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>

                            ) : (
                                <svg className = "w-5 h-5 text-red-600 dark:text-red-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                
                            )}

                            <span className = {`text-sm font-medium ${
                                notification.type === 'success'
                                    ? 'text-green-800 dark:text-green-200'
                                    : 'text-red-800 dark:text-red-200'
                            }`}>
                                {notification.message}
                            </span>
                        </div>

                        <button
                            onClick = {() => setNotification(null)}
                            className = {`${
                                notification.type === 'success'
                                    ? 'text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300'
                                    : 'text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300'
                            }`}
                        >
                            <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}

            {/* tabs */}
            <div className = "border-b border-gray-200 dark:border-slate-700">
                <div className = "flex space-x-1 px-4">
                    <button
                        onClick = {() => setActiveTab('tables')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'tables' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                        }`}
                    >
                        Tables
                    </button>

                    <button
                        onClick = {() => setActiveTab('er')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'er' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                        }`}
                    >
                        ER Diagram
                    </button>
                </div>
            </div>

            {/* tab content */}
            <div className = "flex-1 p-4 overflow-auto">
                {activeTab === 'tables' && (
                    <div>
                        {isDbConnected && (
                            <div className = "space-y-3 mb-4">
                                <div className = "flex items-center justify-between">
                                    <h3 className = "text-sm font-medium text-gray-700 dark:text-gray-300">Schema Tables</h3>

                                    <button
                                        onClick={fetchSchema}
                                        disabled={loading}
                                        className = "text-xs bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 px-3 py-1 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? 'Refreshing...' : 'Refresh'}
                                    </button>
                                </div>

                                {/* Search box */}
                                <div className = "relative">
                                    <svg className = "absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    <input
                                        type = "text"
                                        placeholder = "Search tables..."
                                        value = {searchTerm}
                                        onChange = {(e) => setSearchTerm(e.target.value)}
                                        className = "w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-gray-700 dark:text-gray-300 placeholder-gray-400 dark:placeholder-gray-500"
                                    />
                                    {searchTerm && (
                                        <button
                                            onClick = {() => setSearchTerm('')}
                                            className = "absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                        >
                                            <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                                            </svg>
                                        </button>
                                    )}
                                </div>

                                {/* Table count */}
                                {schema && schema.tables && (
                                    <div className = "text-xs text-gray-500 dark:text-gray-400 text-right">
                                        {searchTerm ? (
                                            <>
                                                {getFilteredTables().length} of {schema.tables.length} table{schema.tables.length !== 1 ? 's' : ''}
                                            </>
                                        ) : (
                                            <>
                                                {schema.tables.length} table{schema.tables.length !== 1 ? 's' : ''}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}

                        {renderTablesList()}
                    </div>
                )}

                {activeTab === 'er' && (
                    <div className = "h-full flex flex-col">
                        {!isDbConnected ? (
                            <div className = "flex flex-col items-center justify-center h-full py-8 px-4 text-center">
                                <svg className = "w-12 h-12 text-gray-400 dark:text-gray-500 mb-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                                </svg>
                                <p className = "text-sm text-gray-600 dark:text-gray-400 mb-2">
                                    No database connected
                                </p>
                                <p className = "text-xs text-gray-500 dark:text-gray-500">
                                    Click the settings icon in the top right to connect to a database
                                </p>
                            </div>
                        ) : loading ? (
                            <div className = "flex items-center justify-center h-full">
                                <div className = "text-sm text-gray-500 dark:text-gray-400">Loading ER diagram...</div>
                            </div>
                        ) : error ? (
                            <div className = "flex items-center justify-center h-full">
                                <div className = "text-sm text-red-600 dark:text-red-400 p-3 bg-red-50 dark:bg-red-900/20 rounded">
                                    {error}
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* diagram filters */}
                                <div className = "space-y-2 mb-3">

                                    {/* undo and redo buttons */}
                                    <div className = "flex items-center space-x-2">
                                        <button
                                            onClick = {handleUndo}
                                            disabled = {undoStack.length === 0 || isUndoRedoInProgress}
                                            className = "flex items-center space-x-1 px-3 py-1.5 text-xs bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-300 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-gray-100 dark:disabled:hover:bg-slate-700"
                                            title = "Undo (Ctrl+Z)"
                                        >
                                            {isUndoRedoInProgress ? (
                                                <svg className = "animate-spin w-4 h-4" fill = "none" viewBox = "0 0 24 24">
                                                    <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                                    <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                            ) : (
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                                                </svg>
                                            )}

                                            <span>Undo</span>

                                            {undoStack.length > 0 && !isUndoRedoInProgress && (
                                                <span className = "text-xs text-gray-500 dark:text-gray-400">({undoStack.length})</span>
                                            )}
                                        </button>

                                        <button
                                            onClick = {handleRedo}
                                            disabled = {redoStack.length === 0 || isUndoRedoInProgress}
                                            className = "flex items-center space-x-1 px-3 py-1.5 text-xs bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-300 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-gray-100 dark:disabled:hover:bg-slate-700"
                                            title = "Redo (Ctrl+Y)"
                                        >
                                            {isUndoRedoInProgress ? (
                                                <svg className = "animate-spin w-4 h-4" fill = "none" viewBox = "0 0 24 24">
                                                    <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                                    <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                            ) : (
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                                                </svg>
                                            )}

                                            <span>Redo</span>

                                            {redoStack.length > 0 && !isUndoRedoInProgress && (
                                                <span className = "text-xs text-gray-500 dark:text-gray-400">({redoStack.length})</span>
                                            )}
                                        </button>
                                    </div>

                                    {/* Search box */}
                                    <div className = "relative">
                                        <svg className = "absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                        </svg>
                                        <input
                                            type = "text"
                                            placeholder = "Filter diagram..."
                                            value = {searchTerm}
                                            onChange = {(e) => setSearchTerm(e.target.value)}
                                            className = "w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-gray-700 dark:text-gray-300 placeholder-gray-400 dark:placeholder-gray-500"
                                        />
                                        {searchTerm && (
                                            <button
                                                onClick = {() => setSearchTerm('')}
                                                className = "absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                            >
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        )}
                                    </div>

                                    {/* table count */}
                                    {schema && schema.tables && (
                                        <div className = "text-xs text-gray-500 dark:text-gray-400 text-right">
                                            {searchTerm ? (
                                                <>
                                                    {getFilteredTables().length} of {schema.tables.length} table{schema.tables.length !== 1 ? 's' : ''}
                                                </>
                                            ) : (
                                                <>
                                                    {schema.tables.length} table{schema.tables.length !== 1 ? 's' : ''}
                                                </>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className = "flex-1 min-h-0">
                                    <ERDiagram
                                        schema = {getFilteredSchema()}
                                        onAskAboutTable = {onAskAboutTable}
                                        onSchemaUpdate = {handleSchemaUpdate}
                                    />
                                </div>
                            </>
                        )}
                    </div>
                )}

            </div>
        </div>
    )

}


export default SchemaExplorerPanel