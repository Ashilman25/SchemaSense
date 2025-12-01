import {memo} from 'react';
import {Handle, Position} from 'reactflow';

//custom node for db tables
const TableNode = memo(({data, selected}) => {
    const {tableName, schema, columns, isExpanded, onToggleExpand, nodeId, onNodeClick} = data;

    const keyColumns = columns.filter(col => col.is_pk || col.is_fk);
    const nonKeyColumns = columns.filter(col => !col.is_pk && !col.is_fk);

    const displayColumns = isExpanded ? columns : keyColumns;

    return (
        <div
            onClick={() => onNodeClick(nodeId)}
            className={`bg-white dark:bg-slate-800 border-2 rounded-lg shadow-lg min-w-[200px] max-w-[300px] cursor-pointer transition-all ${
                selected
                    ? 'border-blue-500 dark:border-blue-400 ring-2 ring-blue-300 dark:ring-blue-600'
                    : 'border-gray-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500'
            }`}
        >

            <Handle type = "target" position = {Position.Top} className = "w-3 h-3 !bg-blue-500" />
            <Handle type = "source" position = {Position.Bottom} className = "w-3 h-3 !bg-blue-500" />

            {/* table header */}
            <div className = "bg-blue-600 dark:bg-blue-700 text-white px-3 py-2 rounded-t-lg">
                <div className = "font-semibold text-sm truncate" title = {`${schema}.${tableName}`}>
                    {tableName}
                </div>

                <div className = "text-xs opacity-80 truncate">
                    {schema}
                </div>
            </div>

            {/* columns */}
            <div className = "p-2">
                {displayColumns.length > 0 ? (
                    <div className = "space-y-1">
                        {displayColumns.map((column, idx) => (
                            <div key = {idx} className = "flex items-center justify-between text-xs py-1 px-2 bg-gray-50 dark:bg-slate-700 rounded gap-2">

                                <div className = "flex flex-col flex-1 min-w-0">

                                    <span className = "font-mono text-gray-700 dark:text-gray-300 truncate font-medium" title = {column.name}>
                                        {column.name}
                                    </span>

                                    <span className = "font-mono text-gray-500 dark:text-gray-400 text-[10px] uppercase" title = {column.type}>
                                        {column.type}
                                    </span>
 
                                </div>

                                <div className = "flex items-center space-x-1 flex-shrink-0">
                                    {column.is_pk && (
                                        <span className = "px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded font-medium text-[10px]" title = "Primary Key">
                                            PK
                                        </span>
                                    )}

                                    {column.is_fk && (
                                        <span className = "px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-medium text-[10px]" title = "Foreign Key">
                                            FK
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className = "text-xs text-gray-500 dark:text-gray-400 italic text-center py-2">
                        No relational keys (PKs or FKs) 
                    </div>
                )}

                {/* expanded section */}
                {nonKeyColumns.length > 0 && (
                    <button 
                        onClick = {(e) => {
                            e.stopPropagation();
                            onToggleExpand(nodeId);
                        }}
                        className = "w-full text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-center mt-2 pt-2 border-t border-gray-200 dark:border-slate-600 transition-colors flex items-center justify-center space-x-1"
                    >
                        {isExpanded ? (
                            <>
                                <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d="M5 15l7-7 7 7" />
                                </svg>
                                <span>Show less</span>
                            </>
                        ) : (
                            <>
                                <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 9l-7 7-7-7" />
                                </svg>
                                <span>+{nonKeyColumns.length} more column{nonKeyColumns.length !== 1 ? 's' : ''}</span>
                            </>
                        )}

                    </button>
                )}
            </div>
        </div>
    );
});

TableNode.displayName = 'TableNode';
export default TableNode;