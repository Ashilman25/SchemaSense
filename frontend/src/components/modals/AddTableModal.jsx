import {useState} from 'react';

const AddTableModal = ({isOpen, onClose, onSubmit}) => {
    const [tableName, setTableName] = useState('');
    const [schema, setSchema] = useState('public');
    const [columns, setColumns] = useState([{
        name: 'id',
        type: 'serial',
        is_pk: true,
        nullable: false
    }]);
    const [error, setError] = useState(null);

    const handleAddColumn = () => {
        setColumns([...columns, {name: '', type: 'text', is_pk: false, nullable: true}]);
    };

    const handleRemoveColumn = (index) => {
        if (columns.length > 1) {
            setColumns(columns.filter((_, i) => i !== index));
        }
    };

    const handleColumnChange = (index, field, value) => {
        const newColumns = [...columns];
        newColumns[index] = {...newColumns[index], [field]: value};
        setColumns(newColumns);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!tableName.trim()) {
            setError('Table name is required');
            return;
        }

        if (columns.length === 0) {
            setError('At least one column is required');
            return;
        }

        for (let i = 0; i < columns.length; i++) {
            if (!columns[i].name.trim()) {
                setError(`Column ${i + 1} name is required`);
                return;
            }

            if (!columns[i].type.trim()) {
                setError(`Column ${i + 1} type is required`);
                return;
            }
        }


        try {
            await onSubmit({
                tableName: tableName.trim(),
                schema: schema.trim(),
                columns
            });
            handleClose();

        } catch (err) {
            setError(err.message || 'Failed to add table');
        }
    };

    const handleClose = () => {
        setTableName('');
        setSchema('public');
        setColumns([{name: 'id', type: 'serial', is_pk: true, nullable: false}]);
        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">

                {/* header */}
                <div className = "bg-blue-600 dark:bg-blue-700 text-white px-6 py-4 flex items-center justify-between">
                    <h2 className = "text-lg font-semibold">Add New Table</h2>

                    <button
                        onClick = {handleClose}
                        className = "text-white hover:bg-blue-700 dark:hover:bg-blue-600 p-1 rounded transition-colors"
                    >
                        <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                        </svg>

                    </button>
                </div>

                <form onSubmit = {handleSubmit} className = "p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
                    
                    {/* table info */}
                    <div className = "space-y-4 mb-6">
                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Table Name
                            </label>

                            <input 
                                type = "text"
                                value = {tableName}
                                onChange = {(e) => setTableName(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                                placeholder = "e.g., users, products, orders"
                                autoFocus                        
                            />
                        </div>

                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Schema
                            </label>

                            <input 
                                type = "text"
                                value = {schema}
                                onChange = {(e) => setSchema(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                                placeholder = "public"
                            />
                        </div>
                    </div>

                </form>
            </div>
        </div>
    );
};

export default AddTableModal;