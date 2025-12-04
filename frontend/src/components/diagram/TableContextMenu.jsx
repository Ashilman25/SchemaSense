import {useEffect, useRef, useState} from 'react';

const TableContextMenu = ({position, onClose, onRename, onDelete, tableName}) => {
    const menuRef = useRef(null);
    const modalRef = useRef(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (modalRef.current && modalRef.current.contains(event.target)) {
                return;
            }

            if (menuRef.current && !menuRef.current.contains(event.target)) {
                onClose();
            }
        };

        const handleEscape = (event) => {
            if (event.key === 'Escape') {
                if (showDeleteModal) {
                    setShowDeleteModal(false);
                } else {
                    onClose();
                }
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };

    }, [onClose, showDeleteModal]);

    if (!position) return null;

    return (
        <>
            <div
                ref = {menuRef}
                className = "fixed bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-xl py-1 z-50 min-w-[160px]"
                style = {{top: position.y, left: position.x}}
            >
            <button
                onClick = {() => {
                    onRename();
                    onClose();
                }}
                className = "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 flex items-center space-x-2"
            >
                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>

                <span>Rename Table</span>
            </button>

            <div className = "border-t border-gray-200 dark:border-slate-600 my-1" />

            <button
                onClick = {() => {
                    setShowDeleteModal(true);
                }}
                className = "w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center space-x-2"
            >
                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>

                <span>Delete Table</span>
            </button>
            </div>

            {showDeleteModal && (
            <div ref = {modalRef} className = "fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60]">
                <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-gray-200 dark:border-slate-600 max-w-md w-full mx-4 animate-in fade-in zoom-in-95 duration-200">
                    
                    <div className = "p-6">
                        <div className = "flex items-start space-x-4">
                            
                            <div className = "flex-shrink-0 w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                                <svg className = "w-6 h-6 text-red-600 dark:text-red-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>

                            <div className = "flex-1">
                                <h3 className = "text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                                    Delete Table
                                </h3>

                                <p className = "text-sm text-gray-600 dark:text-gray-400">
                                    Are you sure you want to delete table <span className = "font-semibold text-gray-900 dark:text-gray-100">"{tableName}"</span>? This action cannot be undone.
                                </p>
                            </div>
                        </div>

                        <div className = "flex justify-end space-x-3 mt-6">
                            <button
                                onClick = {() => {
                                    setShowDeleteModal(false);
                                }}
                                className = "px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors"
                            >
                                Cancel
                            </button>

                            <button
                                onClick = {() => {
                                    onDelete();
                                    setShowDeleteModal(false);
                                    onClose();
                                }}
                                className = "px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 rounded-lg transition-colors"
                            >
                                Delete
                            </button>
                        </div>

                    </div>
                </div>
            </div>
            )}
        </>
    );
};

export default TableContextMenu;