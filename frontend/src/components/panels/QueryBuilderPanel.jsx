import React from "react";

const QueryBuilderPanel = () => {
    return (
        <div className = "h-full bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <h2 className = "text-lg font-semibold text-gray-800 mb-4">Query Builder</h2>

            <div className = "space-y-4">

                {/* english input section */}
                <div>
                    <label className = "block text-sm font-medium text-gray-700 mb-2">
                        Ask a question
                    </label>

                    <textarea 
                        className = "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                        rows = {4}
                        placeholder = "e.g., Show me total revenue by month for the last 6 months"
                    />
                </div>

                <button className = "w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                    Generate SQL
                </button>

                {/* query history section */}
                <div className = "mt-6">
                    <h3 className = "text-sm font-medium text-gray-700 mb-2">Recent Queries</h3>

                    <div className = "space-y-2">
                        <div className = "text-sm text-gray-500 italic">No recent queries</div>
                    </div>
                </div>


            </div>
        </div>
    )
}

export default QueryBuilderPanel