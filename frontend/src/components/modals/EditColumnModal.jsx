import {useState, useEffect} from 'react';

const EditColumnModal = ({isOpen, onClose, onSubmit, column, mode = 'add'}) => {
    const [columnName, setColumnName] = useState('');
    const [columnType, setColumnType] = useState('text');
    const [isPrimaryKey, setIsPrimaryKey] = useState(false);
    const [isForeignKey, setIsForeignKey] = useState(false);
    const [nullable, setNullable] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && column && mode === 'edit') {
            setColumnName(column.name || '');
            setColumnType(column.type || 'text');
            setIsPrimaryKey(column.is_pk || false);
            setIsForeignKey(column.is_fk || false);
            setNullable(column.nullable !== undefined ? column.nullable : true);

        } else if (isOpen && mode === 'add') {
            setColumnName('');
            setColumnType('text');
            setIsPrimaryKey(false);
            setIsForeignKey(false);
            setNullable(true);
        }

        setError(null);

    }, [isOpen, column, mode]);


    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!columnName.trim()) {
            setError("Column name is required");
            return;
        }

        if (!columnType.trim()) {
            setError("Column type is required");
            return;
        }

        try {
            await onSubmit({
                name: columnName.trim(),
                type: columnType.trim(),
                is_pk: isPrimaryKey,
                is_fk: isForeignKey,
                nullable: nullable
            });

            handleClose()

        } catch (err) {
            setError(err.message || `Failed to ${mode} column`);
        }
    };

    const handleClose = () => {
        setColumnName('');
        setColumnType('text');
        setIsPrimaryKey(false);
        setIsForeignKey(false);
        setNullable(true);
        setError(null);
        onClose();
    };

    if (!isOpen) return null;
    return (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md">

                {/* header */}
                <div className = "bg-blue-600 dark:bg-blue-700 text-white px-6 py-4 flex items-center justify-between">
                    <h2 className = "text-lg font-semibold">
                        {mode === 'add' ? 'Add Column' : 'Edit Column'}
                    </h2>

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
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Column Name
                            </label>

                            <input 
                                type = "text"
                                value = {columnName}
                                onChange = {(e) => setColumnName(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                                placeholder = "e.g., email, price"
                                autoFocus
                            />
                        </div>

                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Type
                            </label>

                            <input 
                                type = "text"
                                value = {columnType}
                                onChange = {(e) => setColumnType(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                                placeholder = "e.g., varchar, integer, serial"                            
                            />
                        </div>

                        <div className = "space-y-2">
                            <label className = "flex items-center space-x-2">
                                <input 
                                    type = "checkbox"
                                    checked = {isPrimaryKey}
                                    onChange = {(e) => setIsPrimaryKey(e.target.checked)}
                                    className = "rounded border-gray-300 dark:border-slate-600"
                                />

                                <span className = "text-sm text-gray-700 dark:text-gray-300">Primary Key</span>
                            </label>

                            <label className = "flex items-center space-x-2">
                                <input 
                                    type = "checkbox"
                                    checked = {nullable}
                                    onChange = {(e) => setNullable(e.target.checked)}
                                    className = "rounded border-gray-300 dark:border-slate-600"
                                />

                                <span className = "text-sm text-gray-700 dark:text-gray-300">Nullable</span>
                            </label>
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
                            {mode === 'add' ? 'Add Column' : 'Save Changes'}

                        </button>
                    </div>


                </form>
            </div>
        </div>


    );
};

export default EditColumnModal;