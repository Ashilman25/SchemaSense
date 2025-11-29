import { useState } from "react";

const QueryBuilderPanel = () => {
    const [question, setQuestion] = useState("");

    const placeholderHistory = [
        {
            id: 1,
            question: "Show me total revenue by month for the last 6 months",
            timestamp: "2 hours ago"
        },
        {
            id: 2,
            question: "List the top 10 customers by lifetime spend",
            timestamp: "5 hours ago"
        },
        {
            id: 3,
            question: "What are the most popular products?",
            timestamp: "Yesterday"
        }
    ];

    return (
        <div className = "h-full bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-gray-200 dark:border-slate-700 p-4 transition-colors flex flex-col">
            <h2 className = "text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Query Builder</h2>

            <div className = "flex-1 flex flex-col space-y-4 overflow-hidden">

                {/* english input section */}
                <div>
                    <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Ask a question
                    </label>

                    <textarea
                        value = {question}
                        onChange = {(e) => setQuestion(e.target.value)}
                        className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors"
                        rows = {4}
                        placeholder = "e.g., Show me total revenue by month for the last 6 months"
                    />
                </div>

                <button className = "w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                    Generate SQL
                </button>

                {/* query history section */}
                <div className = "flex-1 flex flex-col min-h-0">
                    <h3 className = "text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Recent Queries</h3>

                    <div className = "flex-1 overflow-y-auto space-y-2">
                        {placeholderHistory.map((item) => (
                            <div key={item.id} className = "p-3 bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg border border-gray-200 dark:border-slate-600 cursor-pointer transition-colors">
                                <p className = "text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                                    {item.question}
                                </p>
                                <p className = "text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {item.timestamp}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>


            </div>
        </div>
    )
}

export default QueryBuilderPanel