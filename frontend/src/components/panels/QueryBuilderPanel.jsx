import { useState } from "react";
import { nlToSqlAPI } from "../../utils/api";

const QueryBuilderPanel = ({ onSqlGenerated, question, onQuestionChange }) => {
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

    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [warnings, setWarnings] = useState([]);

    const handleGenerate = async () => {
        if (!question.trim()) {
            setError('Please enter a question');
            return;
        }

        setError('');
        setWarnings([]);
        setIsLoading(true);

        try {
            const response = await nlToSqlAPI.generateSQL(question);

            // On success, populate SQL editor and display warnings
            if (response.sql) {
                onSqlGenerated(response.sql, response.warnings || []);
                setWarnings(response.warnings || []);
            }
        } catch (err) {
            setError(err.message || 'Failed to generate SQL');
        } finally {
            setIsLoading(false);
        }
    };

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
                        onChange = {(e) => onQuestionChange(e.target.value)}
                        className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors"
                        rows = {4}
                        placeholder = "e.g., Show me total revenue by month for the last 6 months"
                    />

                    {/* Inline error display */}
                    {error && (
                        <div className = "mt-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                            {error}
                        </div>
                    )}
                </div>

                {/* Generate SQL button with loading indicator */}
                <button
                    onClick = {handleGenerate}
                    disabled = {isLoading}
                    className = "w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                    {isLoading ? (
                        <>
                            <svg className = "animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Generating...
                        </>
                    ) : (
                        'Generate SQL'
                    )}
                </button>

                {/* Warnings display */}
                {warnings.length > 0 && (
                    <div className = "bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-3">
                        <h4 className = "text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-2">Warnings:</h4>
                        <ul className = "space-y-1">
                            {warnings.map((warning, idx) => (
                                <li key = {idx} className = "text-sm text-yellow-700 dark:text-yellow-400 flex items-start">
                                    <svg className = "w-4 h-4 mr-2 mt-0.5 flex-shrink-0" fill = "currentColor" viewBox = "0 0 20 20">
                                        <path fillRule = "evenodd" d = "M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule = "evenodd" />
                                    </svg>
                                    {warning}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

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
