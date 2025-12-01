import {useState, useEffect} from 'react';
import {schemaAPI} from '../../utils/api';

const TableDetailPanel = ({table, schema, onClose, onAskAboutTable}) => {
    const [sampleRows, setSampleRows] = useState(null);
    const [loadingSampleRows, setLoadingSampleRows] = useState(false);
    const [sampleRowsError, setSampleRowsError] = useState(null);

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
    }


    return (
        <div className = "absolute top-0 right-0 h-full w-80 bg-white dark:bg-slate-800 border-l border-gray-300 dark:border-slate-600 shadow-lg overflow-y-auto z-10">

            {/* panel header */}
            <div className = "sticky top-0 bg-blue-600 dark:bg-blue-700 text-white px-4 py-3 flex items-center justify-between">
                <div className = "flex-1 min-w-0">
                    <h3 className = "font-semibold text-sm" title = {`${table.schema}.${table.name}`}>
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
                    <h4 className = "text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        Columns ({table.columns.length})
                    </h4>

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
                                </div>
                            </div>

                        ))}
                    </div>
                </div>























            </div>
        </div>
    );
};

export default TableDetailPanel;