import {useState, useEffect} from 'react';
import {schemaAPI} from '../../utils/api';
import EditColumnModal from '../modals/EditColumnModal';
import AddRelationshipModal from '../modals/AddRelationshipModal';

const TableDetailPanel = ({table, schema, onClose, onAskAboutTable, onSchemaUpdate}) => {
    const [sampleRows, setSampleRows] = useState(null);
    const [loadingSampleRows, setLoadingSampleRows] = useState(false);
    const [sampleRowsError, setSampleRowsError] = useState(null);

    const [showAddColumnModal, setShowAddColumnModal] = useState(false);
    const [showEditColumnModal, setShowEditColumnModal] = useState(false);
    const [editingColumn, setEditingColumn] = useState(null);
    const [showAddRelationshipModal, setShowAddRelationshipModal] = useState(false);

    const tableKey = `${table.schema}.${table.name}`;

    useEffect(() => {
        setSampleRows(null);
        setSampleRowsError(null);
    }, [tableKey]);

    //relations
    const outgoingFKs = schema.relationships?.filter(rel => rel.from_table === tableKey) || [];
    const incomingFKs = schema.relationships?.filter(rel => rel.to_table === tableKey) || [];

    const handlePreviewSampleRows = async () => {
        setLoadingSampleRows(true);
        setSampleRowsError(null);

        try {
            const data = await schemaAPI.getSampleRows(tableKey, 10);
            setSampleRows(data);

        } catch (err) {
            setSampleRowsError(err.message || 'Failed to load sample rows');

        } finally {
            setLoadingSampleRows(false);
        }
    };

    const handleAskAboutTable = () => {
        onAskAboutTable(tableKey);
        //onClose();
    };

    const handleAddColumn = async (columnData) => {
        try {
            const actions = [{
                type: 'add_column',
                table: tableKey,
                column: columnData
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to add column');
            }

        } catch (error) {
            console.error('Failed to add column:', error);
            throw error;
        }
    };

    const handleEditColumn = async (columnData) => {
        if (!editingColumn) return;

        try {
            const actions = [{
                type: 'rename_column',
                table: tableKey,
                old_col: editingColumn.name,
                new_col: columnData.name
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to edit column');
            }

        } catch (error) {
            console.error('Failed to edit column:', error);
            throw error;
        }
    };

    const handleDeleteColumn = async (columnName) => {
        if (!window.confirm(`Are you sure you want to delete column "${columnName}"?`)) {
            return;
        }

        try {
            const actions = [{
                type: 'drop_column',
                table: tableKey,
                column_name: columnName,
                force: false
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to delete column');
            }

        } catch (error) {
            console.error('Failed to delete column:', error);
            alert(`Failed to delete column: ${error.message}`);
        }
    };

    const handleAddRelationship = async (relationshipData) => {
        try {
            const actions = [{
                type: 'add_relationship',
                from_table: relationshipData.from_table,
                from_column: relationshipData.from_column,
                to_table: relationshipData.to_table,
                to_column: relationshipData.to_column
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to add relationship');
            }

        } catch (error) {
            console.error('Failed to add relationship:', error);
            throw error;
        }
    };

    const handleDeleteRelationship = async (relationship) => {
        if (!window.confirm(`Are you sure you want to delete the relationship from ${relationship.from_column} to ${relationship.to_table}.${relationship.to_column}?`)) {
            return;
        }

        try {
            const actions = [{
                type: 'remove_relationship',
                from_table: relationship.from_table,
                from_column: relationship.from_column,
                to_table: relationship.to_table,
                to_column: relationship.to_column
            }];

            const response = await schemaAPI.applyEREdits(actions);

            if (response.success) {
                onSchemaUpdate(response.schema, response.ddl);

            } else {
                throw new Error(response.errors?.join(', ') || 'Failed to delete relationship');
            }

        } catch (error) {
            console.error('Failed to delete relationship:', error);
            alert(`Failed to delete relationship: ${error.message}`);
        }
    };


    return (
        <div className = "absolute top-0 right-0 h-full w-80 bg-white dark:bg-slate-800 border-l border-gray-300 dark:border-slate-600 shadow-lg overflow-y-auto z-10">

            {/* panel header */}
            <div className = "sticky top-0 bg-blue-600 dark:bg-blue-700 text-white px-4 py-3 flex items-center justify-between">
                <div className = "flex-1 min-w-0">
                    <h3 className = "font-semibold text-sm truncate" title = {`${table.schema}.${table.name}`}>
                        {table.name}
                    </h3>

                    <p className = "text-xs opacity-80 truncate">
                        {table.schema}
                    </p>
                </div>

                <button
                    type = "button"
                    onClick = {onClose}
                    className = "ml-2 text-white hover:bg-blue-700 dark:hover:bg-blue-600 p-1 rounded transition-colors"
                >
                    <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>


            {/* panel content */}
            <div className = "p-4 space-y-4">

                {/* ask about button */}
                <button
                    type = "button"
                    onClick = {handleAskAboutTable}
                    className = "w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center space-x-2"
                >
                    <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>

                    <span>Ask about this table</span>
                </button>

                {/* columns */}
                <div>
                    <div className = "flex items-center justify-between mb-2">
                        <h4 className = "text-sm font-semibold text-gray-700 dark:text-gray-300">
                            Columns ({table.columns.length})
                        </h4>

                        <button
                            onClick = {() => setShowAddColumnModal(true)}
                            className = "text-xs bg-green-100 dark:bg-green-900/30 hover:bg-green-200 dark:hover:bg-green-800/50 text-green-700 dark:text-green-300 px-2 py-1 rounded transition-colors flex items-center space-x-1"
                            title = "Add new column"
                        >
                            <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 4v16m8-8H4" />
                            </svg>

                            <span>Add</span>
                        </button>
                    </div>

                    <div className = "space-y-1">
                        {table.columns.map((column, idx) => (
                            <div key = {idx} className = "text-xs p-2 bg-gray-50 dark:bg-slate-700 rounded">
                                <div className = "flex items-start justify-between gap-2">
                                    <div className = "flex-1 min-w-0">
                                        <div className = "flex items-center space-x-1">

                                            <span className = "font-mono font-medium text-gray-700 dark:text-gray-300 truncate" title={column.name}>
                                                {column.name}
                                            </span>

                                            {column.is_pk && (
                                                <span className = "px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded font-medium text-[10px]" title="Primary Key">
                                                    PK
                                                </span>
                                            )}

                                            {column.is_fk && (
                                                <span className = "px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-medium text-[10px]" title="Foreign Key">
                                                    FK
                                                </span>
                                            )}

                                        </div>

                                        <div className = "mt-1 font-mono text-gray-500 dark:text-gray-400 uppercase text-[10px]">
                                            {column.type}
                                        </div>

                                        <div className = "mt-1 text-gray-500 dark:text-gray-400">
                                            {column.nullable ? 'Nullable' : 'Not Null'}
                                        </div>

                                    </div>

                                    {/*  CTAs */}
                                    <div className = "flex items-center space-x-1">
                                        <button
                                            onClick = {() => {
                                                setEditingColumn(column);
                                                setShowEditColumnModal(true);
                                            }}
                                            className = "text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                                            title = "Edit column"
                                        >
                                            <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                            </svg>
                                        </button>

                                        <button
                                            onClick = {() => handleDeleteColumn(column.name)}
                                            className = "text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                            title = "Delete column"
                                        >
                                            <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>

                                </div>
                            </div>
                        ))}
                    </div>
                </div>


                {/* relations */}
                <div>
                    <div className = "flex items-center justify-between mb-2">
                        <h4 className = "text-sm font-semibold text-gray-700 dark:text-gray-300">
                            Relationships
                        </h4>

                        <button
                            onClick = {() => setShowAddRelationshipModal(true)}
                            className = "text-xs bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-800/50 text-purple-700 dark:text-purple-300 px-2 py-1 rounded transition-colors flex items-center space-x-1"
                            title = "Add new foreign key relationship"
                        >
                            <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth  ={2} d = "M12 4v16m8-8H4" />
                            </svg>

                            <span>Add FK</span>
                        </button>
                    </div>

                    {(outgoingFKs.length > 0 || incomingFKs.length > 0) ? (
                        <div className="space-y-3">

                        {/* outgoing FKs, like the table that is being referenced from this table*/}
                        {outgoingFKs.length > 0 && (
                            <div className = "mb-3">
                                <h5 className = "text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                                    References (Outgoing)
                                </h5>

                                <div className = "space-y-1">
                                    {outgoingFKs.map((rel, idx) => (
                                        <div key = {idx} className = "text-xs p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
                                            <div className = "flex items-center justify-between gap-2">
                                                <div className = "flex items-center space-x-1 flex-1 min-w-0">
                                                    <span className = "font-mono text-blue-700 dark:text-blue-400">
                                                        {rel.from_column}
                                                    </span>

                                                    <svg className = "w-3 h-3 text-blue-600 dark:text-blue-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M14 5l7 7m0 0l-7 7m7-7H3" />
                                                    </svg>

                                                    <span className = "font-mono text-blue-700 dark:text-blue-400 truncate">
                                                        {rel.to_table}.{rel.to_column}
                                                    </span>
                                                </div>

                                                <button
                                                    onClick = {() => handleDeleteRelationship(rel)}
                                                    className = "text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex-shrink-0"
                                                    title = "Delete relationship"
                                                >
                                                    <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                    </svg>
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                            </div>
                        )}

                        {/* incoming fks, like the tables that reference this table */}
                        {incomingFKs.length > 0 && (
                            <div>
                                <h5 className = "text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                                    Referenced By (Incoming)
                                </h5>

                                <div className = "space-y-1">
                                    {incomingFKs.map((rel, idx) => (
                                        <div key = {idx} className = "text-xs p-2 bg-green-50 dark:bg-green-900/20 rounded">
                                            <div className = "flex items-center space-x-1">
                                                <span className = "font-mono text-green-700 dark:text-green-400">
                                                    {rel.from_table}.{rel.from_column}
                                                </span>
                                                
                                                <svg className = "w-3 h-3 text-green-600 dark:text-green-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M14 5l7 7m0 0l-7 7m7-7H3" />
                                                </svg>

                                                <span className = "font-mono text-green-700 dark:text-green-400">
                                                    {rel.to_column}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        </div>
                    ) : (
                        <div className = "text-xs text-gray-500 dark:text-gray-400 text-center py-4 bg-gray-50 dark:bg-slate-700/50 rounded">
                            No relationships defined
                        </div>
                    )}
                </div>



                {/* sample rows preview */}
                <div>
                    <h4 className = "text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        Sample Data
                    </h4>

                    {!sampleRows ? (
                        <button
                            type = "button"
                            onClick = {handlePreviewSampleRows}
                            disabled = {loadingSampleRows}
                            className = "w-full bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loadingSampleRows ? 'Loading...' : 'Preview Sample Rows'}
                        </button>
                    ) : (
                        <div className = "space-y-2">
                            <div className = "flex items-center justify-between">
                                <span className = "text-xs text-gray-600 dark:text-gray-400">
                                    Showing {sampleRows.row_count} row{sampleRows.row_count !== 1 ? 's' : ''}
                                </span>

                                <button
                                    type = "button"
                                    onClick = {() => setSampleRows(null)}
                                    className = "text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                                >
                                    Hide
                                </button>
                            </div>

                            <div className = "overflow-x-auto border border-gray-200 dark:border-slate-600 rounded">
                                <table className = "min-w-full text-xs">
                                    <thead className = "bg-gray-50 dark:bg-slate-700">
                                        <tr>
                                            {sampleRows.columns.map((col, idx) => (
                                                <th key = {idx} className = "px-2 py-1 text-left font-mono font-medium text-gray-700 dark:text-gray-300">
                                                    {col}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>

                                    <tbody className = "bg-white dark:bg-slate-800">
                                        {sampleRows.rows.map((row, rowIdx) => (
                                            <tr key = {rowIdx} className = "border-t border-gray-200 dark:border-slate-600">
                                                {row.map((cell, cellIdx) => (
                                                    <td 
                                                        key = {cellIdx} 
                                                        className = "px-2 py-1 font-mono text-gray-600 dark:text-gray-400 whitespace-nowrap"
                                                        title = {String(cell)}
                                                    >
                                                        {cell === null ? (
                                                            <span className = "italic text-gray-400 dark:text-gray-500">null</span>
                                                        ) : (
                                                            String(cell).length > 20 ? String(cell).substring(0, 20) + '...' : String(cell)
                                                        )}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {sampleRowsError && (
                        <div className = "text-xs text-red-600 dark:text-red-400 p-2 bg-red-50 dark:bg-red-900/20 rounded">
                            {sampleRowsError}
                        </div>
                    )}

                </div>
            </div>

            <EditColumnModal
                isOpen = {showAddColumnModal}
                onClose = {() => setShowAddColumnModal(false)}
                onSubmit = {handleAddColumn}
                mode = "add"
            />

            <EditColumnModal
                isOpen = {showEditColumnModal}
                onClose = {() => {
                    setShowEditColumnModal(false);
                    setEditingColumn(null);
                }}
                onSubmit = {handleEditColumn}
                column = {editingColumn}
                mode = "edit"
            />

            <AddRelationshipModal
                isOpen = {showAddRelationshipModal}
                onClose = {() => setShowAddRelationshipModal(false)}
                onSubmit = {handleAddRelationship}
                schema = {schema}
                currentTable = {table}
            />
        </div>
    );
};

export default TableDetailPanel;