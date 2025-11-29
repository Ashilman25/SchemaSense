import React, {useState, useEffect} from "react";
import { schemaAPI } from "../../utils/api";

const SchemaExplorerPanel = ({ onAskAboutTable }) => {
    const [activeTab, setActiveTab] = useState('tables')
    const [schema, setSchema] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedTables, setExpandedTables] = useState(new Set());

    useEffect(() => {
        fetchSchema();
    }, []);

    const fetchSchema = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await schemaAPI.getSchema();
            setSchema(data);

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

    const renderTablesList = () => {
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
                    Connect to a database to view schema tables
                </div>
            );
        }

        return (
            <div className = "space-y-2">
                {schema.tables.map((table) => {
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
        <div className = "h-full bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-gray-200 dark:border-slate-700 flex flex-col transition-colors">

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
                        <div className = "flex items-center justify-between mb-4">
                            <h3 className = "text-sm font-medium text-gray-700 dark:text-gray-300">Schema Tables</h3>

                            <button
                                onClick={fetchSchema}
                                disabled={loading}
                                className = "text-xs bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 px-3 py-1 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Refreshing...' : 'Refresh'}
                            </button>
                        </div>

                        {renderTablesList()}
                    </div>
                )}

                {activeTab === 'er' && (
                    <div className = "h-full flex items-center justify-center">
                        <div className = "text-sm text-gray-500 dark:text-gray-400">
                            Connect to a database to view ER diagram
                        </div>
                    </div>
                )}


            </div>
        </div>
    )

}


export default SchemaExplorerPanel