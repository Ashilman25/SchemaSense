import {useState, useEffect} from 'react';

const RenameTableModal = ({isOpen, onClose, onSubmit, currentName}) => {
    const [newName, setNewName] = useState('');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen) {
            setNewName(currentName || '');
            setError(null);
        }
    }, [isOpen, currentName]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!newName.trim()) {
            setError('Table name is required');
            return;
        }

        if (newName.trim() === currentName) {
            setError("New name must be different from current name");
            return;
        }

        try {
            await onSubmit(newName.trim());
            handleClose();

        } catch (err) {
            setError(err.message || "Failed to rename table");
        }
    };

    const handleClose = () => {
        setNewName('');
        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md">

                {/* header */}
                <div className = "bg-blue-600 dark:bg-blue-700 text-white px-6 py-4 flex items-center justify-between">
                    <h2 className = "text-lg font-semibold">Rename Table</h2>

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
                                Current Name
                            </label>

                            <div className = "px-3 py-2 bg-gray-100 dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg text-gray-900 dark:text-gray-100">
                                {currentName}                                
                            </div>
                        </div>

                        <div>
                            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                New Name
                            </label>

                            <input 
                                type = "text"
                                value = {newName}
                                onChange = {(e) => setNewName(e.target.value)}
                                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                                placeholder = "Enter new table name"
                                autoFocus                                
                            />
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
                            Rename Table
                        </button>
                    </div>

                </form>
            </div>
        </div>
    );




};

export default RenameTableModal;