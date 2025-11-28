import React, {useState} from "react";

const SchemaExplorerPanel = () => {
    const [activeTab, setActiveTab] = useState('tables')

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

                            <button className = "text-xs bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 px-3 py-1 rounded transition-colors">
                                Refresh
                            </button>
                        </div>

                        <div className = "text-sm text-gray-500 dark:text-gray-400">
                            Connect to a database to view schema tables
                        </div>
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