import {useState, useEffect} from 'react';

const AddRelationshipModal = ({isOpen, onClose, onSubmit, schema, currentTable}) => {
    const [fromColumn, setFromColumn] = useState('');
    const [toTable, setToTable] = useState('');
    const [toColumn, setToColumn] = useState('');
    const [error, setError] = useState(null);

    const availableColumns = currentTable?.columns || [];
    const availableTables = schema?.tables?.filter(t => `${t.schema}.${t.name}` !== `${currentTable?.schema}.${currentTable?.name}`) || [];

    
    const selectedTable = availableTables.find(t => `${t.schema}.${t.name}` === toTable);
    const availableTargetColumns = selectedTable?.columns || [];

    useEffect(() => {
        if (isOpen) {
            setFromColumn('');
            setToTable('');
            setToColumn('');
            setError(null);
        }

    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!fromColumn) {
            setError("Please select a column from the current table");
            return;
        }

        if (!toTable) {
            setError("Please select a target table");
            return;
        }

        if (!toColumn) {
            setError("Please select a target column");
            return;
        }

        try {
            await onSubmit({
                from_table: `${currentTable.schema}.${currentTable.name}`,
                from_column: fromColumn,
                to_table: toTable,
                to_column: toColumn
            });

            handleClose();

        } catch (err) {
            setError(err.message || 'Failed to add relationship');
        }
    };

    const handleClose = () => {
        setFromColumn('');
        setToTable('');
        setToColumn('');
        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md">

                {/* header */}
                <div className = "bg-blue-600 dark:bg-blue-700 text-white px-6 py-4 flex items-center justify-between">
                    <h2 className = "text-lg font-semibold">Add Foreign Key Relationship</h2>

                    <button
                        onClick = {handleClose}
                        className = "text-white hover:bg-blue-700 dark:hover:bg-blue-600 p-1 rounded transition-colors"
                    >
                        <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>



                {/* content */}
                <form onSubmit = {handleSubmit} className = "p-6">
                    <div className = "space-y-4 mb-6">

                        {/* from table (current table) */}
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                From Table
                            </label>

                            <div className = "px-3 py-2 bg-gray-100 dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg text-gray-900 dark:text-gray-100">
                                {currentTable?.schema}.{currentTable?.name}
                            </div>
                        </div>



                        {/* from col */}
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                From Column
                            </label>

                            <select
                                value = {fromColumn}
                                onChange = {(e) => setFromColumn(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                            >
                                <option value = "">Select a column...</option>
                                {availableColumns.map((col, idx) => (
                                    <option key = {idx} value = {col.name}>
                                        {col.name} ({col.type})
                                    </option>
                                ))}
                                
                            </select>
                        </div>



                        {/* arrow indactor */}
                        <div className = "flex items-center justify-center text-gray-500 dark:text-gray-400">
                            <svg className = "w-6 h-6" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                        </div>


                        {/* to table */}
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                References Table
                            </label>

                            <select
                                value = {toTable}
                                onChange = {(e) => {
                                    setToTable(e.target.value);
                                    setToColumn('');
                                }}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                            >
                                <option value = "">Select a table...</option>
                                {availableTables.map((table, idx) => (
                                    <option key = {idx} value = {`${table.schema}.${table.name}`}>
                                        {table.schema}.{table.name}
                                    </option>
                                ))}
                            </select>
                        </div>


                        {/* to col */}
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                References Column
                            </label>

                            <select
                                value = {toColumn}
                                onChange = {(e) => setToColumn(e.target.value)}
                                disabled = {!toTable}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <option value = "">Select a column...</option>
                                {availableTargetColumns.map((col, idx) => (
                                    <option key = {idx} value = {col.name}>
                                        {col.name} ({col.type})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* info note */}
                        <div className = "p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                            <p className = "text-xs text-blue-700 dark:text-blue-300">
                                This will create a foreign key constraint from {currentTable?.name}.{fromColumn || '...'} to {toTable ? toTable.split('.')[1] : '...'}.{toColumn || '...'}
                            </p>
                        </div>

                    </div>



                    {/* err msg */}
                    {error && (
                        <div className = "mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <p className = "text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    )}


                    {/* CTAs */}
                    <div className = "flex items-center justify-end space-x-3">
                        <button
                            type = "button"
                            onClick = {handleClose}
                            className = "px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>

                        <button
                            type = "submit"
                            className = "px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white rounded-lg transition-colors"
                        >
                            Add Relationship
                        </button>
                    </div>


                </form>
            </div>
        </div>

    );
};

export default AddRelationshipModal;