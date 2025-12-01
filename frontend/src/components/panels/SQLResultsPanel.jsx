import {useState, useEffect} from 'react';
import CodeMirror from '@uiw/react-codemirror';
import {sql} from '@codemirror/lang-sql';
import {oneDark} from '@codemirror/theme-one-dark';
import {useTheme} from '../../context/ThemeContext';
import {format} from 'sql-formatter';
import { sqlAPI } from '../../utils/api';
import QueryPlanVisualization from '../QueryPlanVisualization';


const SQLResultsPanel = ({ generatedSql, warnings }) => {
    const {theme} = useTheme();
    const [activeTab, setActiveTab] = useState('query');
    const [querySql, setQuerySql] = useState('-- Your generated SQL will appear here');
    const [schemaSql, setSchemaSql] = useState('-- Schema DDL will appear here once connected');
    const [isEditable, setIsEditable] = useState(false);

    const [queryResults, setQueryResults] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const [queryPlan, setQueryPlan] = useState(null);
    const [planError, setPlanError] = useState('');
    const [isPlanLoading, setIsPlanLoading] = useState(false);

    useEffect(() => {
        if (generatedSql) {
            try {
                const formattedSql = format(generatedSql, {
                    language: 'postgresql',
                    tabWidth: 2,
                    keywordCase: 'upper',
                    linesBetweenQueries: 2,
                });
                setQuerySql(formattedSql);

            } catch (error) {
                console.error('SQL formatting error:', error);
                setQuerySql(generatedSql);
            }
        }
    }, [generatedSql]);

    const handleExecuteQuery = async () => {
        if (!querySql.trim() || querySql.trim().startsWith('--')) {
            setError('Please enter a SQL query to execute');
            return;
        }

        setError('');
        setIsLoading(true);
        setQueryResults(null);

        try {
            const response = await sqlAPI.execute(querySql);

            if (response.error_type) {
                setError(response.message || 'Query execution failed');
                setQueryResults(null);

            } else {
                setQueryResults(response);
                setError('');
            }

        } catch (err) {
            setError(err.message || 'Failed to execute query');
            setQueryResults(null);

        } finally {
            setIsLoading(false);
        }
    };

    const handlePlanQuery = async () => {
        if (!querySql.trim() || querySql.trim().startsWith('--')) {
            setPlanError('Please enter a SQL query to generate plan for');
            return;
        }

        setPlanError('');
        setIsPlanLoading(true);
        setQueryPlan(null);

        try {
            const response = await sqlAPI.getPlan(querySql);

            if (response.error_type) {
                setPlanError(response.message || 'Query plan generation failed');
                setQueryPlan(null);
            } else {
                setQueryPlan(response);
                setPlanError('');
            }
        } catch (err) {
            setPlanError(err.message || 'Failed to generate query plan');
            setQueryPlan(null);
        } finally {
            setIsPlanLoading(false);
        }
    };



    return (
        <div className = "h-full bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-gray-200 dark:border-slate-700 flex flex-col transition-colors">

            {/* tabs */}
            <div className = "border-b border-gray-200 dark:border-slate-700">
                <div className = "flex space-x-1 px-4">
                    <button
                        onClick = {() => setActiveTab('query')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'query' ? 'border-blue-500 text-blue-600 dark:text-blue-400': 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                        }`}
                    >
                        Query SQL
                    </button>

                    <button
                        onClick = {() => setActiveTab('plan')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'plan' ? 'border-blue-500 text-blue-600 dark:text-blue-400': 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                        }`}
                    >
                        Query Plan
                    </button>

                    <button
                        onClick = {() => setActiveTab('schema')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'schema' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                        }`}
                    >
                        Schema SQL
                    </button>
                </div>
            </div>

            {/* tab content */}
            <div className = "flex-1 p-4 overflow-auto">
                {activeTab === 'query' && (
                    <div className = "h-full flex flex-col">

                        {/* sql editor */}
                        <div className = "flex-1 min-h-[200px] rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                            <CodeMirror
                                value = {querySql}
                                height = "100%"
                                minHeight = "200px"
                                extensions = {[sql()]}
                                onChange = {(value) => setQuerySql(value)}
                                editable = {isEditable}
                                readOnly = {!isEditable}
                                theme = {theme === 'dark' ? oneDark : 'light'}
                                className = "h-full"
                                basicSetup = {{
                                    lineNumbers: true,
                                    highlightActiveLineGutter: true,
                                    highlightSpecialChars: true,
                                    foldGutter: true,
                                    drawSelection: true,
                                    dropCursor: true,
                                    allowMultipleSelections: true,
                                    indentOnInput: true,
                                    syntaxHighlighting: true,
                                    bracketMatching: true,
                                    closeBrackets: true,
                                    autocompletion: true,
                                    rectangularSelection: true,
                                    crosshairCursor: true,
                                    highlightActiveLine: true,
                                    highlightSelectionMatches: true,
                                    closeBracketsKeymap: true,
                                    searchKeymap: true,
                                    foldKeymap: true,
                                    completionKeymap: true,
                                    lintKeymap: true,
                                }}
                            />
                        </div>

                        {/* run query button */}
                        <div className = "mt-4 flex items-center space-x-2">
                            <button
                                onClick={handleExecuteQuery}
                                disabled={isLoading}
                                className = {`
                                    bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600
                                    text-white font-medium py-2 px-4 rounded-lg transition-colors
                                    flex items-center space-x-2
                                    ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                                `}
                            >
                                {isLoading && (
                                    <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                        <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                        <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                )}
                                <span>{isLoading ? 'Running...' : 'Run Query'}</span>
                            </button>

                            <label className = "flex items-center text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                                <input
                                    type = "checkbox"
                                    className = "mr-2"
                                    checked={isEditable}
                                    onChange={(e) => setIsEditable(e.target.checked)}
                                />
                                Unlock editing
                            </label>
                        </div>

                        {/* results area */}
                        <div className = "mt-4 flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden transition-colors flex flex-col">

                            {/* Error Message */}
                            {error && (
                                <div className="m-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                    <div className="flex items-start">
                                        <svg className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                        </svg>
                                        <div>
                                            <h3 className="text-sm font-medium text-red-800 dark:text-red-300">Query Error</h3>
                                            <p className="mt-1 text-sm text-red-700 dark:text-red-400">{error}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Loading State */}
                            {isLoading && !error && (
                                <div className="flex-1 flex items-center justify-center p-8">
                                    <div className="text-center">
                                        <svg className="animate-spin h-8 w-8 text-blue-600 dark:text-blue-400 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <p className="text-sm text-gray-600 dark:text-gray-400">Executing query...</p>
                                    </div>
                                </div>
                            )}

                            {/* Results Table */}
                            {queryResults && !isLoading && !error && (
                                <div className="flex-1 flex flex-col overflow-hidden">
                                    {/* Results Header */}
                                    <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between bg-white dark:bg-slate-800">
                                        <div className="flex items-center space-x-4">
                                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                                Row count: <span className="text-blue-600 dark:text-blue-400">{queryResults.row_count}</span>
                                            </span>
                                            {queryResults.truncated && (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800">
                                                    Results truncated to {queryResults.row_count} rows
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Table Container */}
                                    <div className="flex-1 overflow-auto">
                                        <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
                                            <thead className="bg-gray-100 dark:bg-slate-700 sticky top-0">
                                                <tr>
                                                    {queryResults.columns && queryResults.columns.map((column, idx) => (
                                                        <th
                                                            key={idx}
                                                            className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider"
                                                        >
                                                            {column}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white dark:bg-slate-900 divide-y divide-gray-200 dark:divide-slate-700">
                                                {queryResults.rows && queryResults.rows.length > 0 ? (
                                                    queryResults.rows.map((row, rowIdx) => (
                                                        <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                                                            {row.map((cell, cellIdx) => (
                                                                <td
                                                                    key={cellIdx}
                                                                    className="px-4 py-3 text-sm text-gray-900 dark:text-gray-200 whitespace-nowrap"
                                                                >
                                                                    {cell === null ? (
                                                                        <span className="text-gray-400 dark:text-gray-500 italic">null</span>
                                                                    ) : (
                                                                        String(cell)
                                                                    )}
                                                                </td>
                                                            ))}
                                                        </tr>
                                                    ))
                                                ) : (
                                                    <tr>
                                                        <td
                                                            colSpan={queryResults.columns?.length || 1}
                                                            className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400"
                                                        >
                                                            No results found
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Empty State */}
                            {!queryResults && !isLoading && !error && (
                                <div className="flex-1 flex items-center justify-center p-8">
                                    <div className="text-center">
                                        <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                            Query results will appear here
                                        </p>
                                        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                                            Click "Run Query" to execute the SQL
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>
                )}

                {activeTab === 'plan' && (
                    <div className = "h-full flex flex-col">

                        {/* plan button */}
                        <div className = "mb-4">
                            <button
                                onClick = {handlePlanQuery}
                                disabled = {isPlanLoading}
                                className = {`
                                    bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600
                                    text-white font-medium py-2 px-4 rounded-lg transition-colors
                                    flex items-center space-x-2
                                    ${isPlanLoading ? 'opacity-50 cursor-not-allowed' : ''}
                                `}
                            >
                                {isPlanLoading && (
                                    <svg className = "animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                        <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                        <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                )}
                                <span>{isPlanLoading ? 'Generating Plan...' : 'Show Plan'}</span>
                            </button>
                        </div>

                        {/* plan visuals area */}
                        <div className = "flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden transition-colors">
                            {/* error message*/}
                            {planError && (
                                <div className = "m-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                    <div className = "flex items-start">
                                        <svg className = "h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                        </svg>
                                        <div>
                                            <h3 className = "text-sm font-medium text-red-800 dark:text-red-300">Plan Generation Error</h3>
                                            <p className = "mt-1 text-sm text-red-700 dark:text-red-400">{planError}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* loading */}
                            {isPlanLoading && !planError && (
                                <div className = "flex-1 flex items-center justify-center p-8">
                                    <div className = "text-center">
                                        <svg className = "animate-spin h-8 w-8 text-purple-600 dark:text-purple-400 mx-auto mb-4" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                            <circle className = "opacity-25" cx = "12" cy="12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                            <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <p className = "text-sm text-gray-600 dark:text-gray-400">Generating query plan...</p>
                                    </div>
                                </div>
                            )}

                            {/*plan visuals */}
                            {!isPlanLoading && !planError && (
                                <div className = "h-full">
                                    <QueryPlanVisualization planData = {queryPlan} />
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'schema' && (
                    <div className = "h-full">

                        {/* schema editor */}
                        <div className = "h-full min-h-[400px] rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                            <CodeMirror
                                value = {schemaSql}
                                height = "100%"
                                minHeight = "400px"
                                extensions = {[sql()]}
                                onChange = {(value) => setSchemaSql(value)}
                                editable = {false}
                                readOnly = {true}
                                theme = {theme === 'dark' ? oneDark : 'light'}
                                basicSetup = {{
                                    lineNumbers: true,
                                    highlightActiveLineGutter: false,
                                    highlightSpecialChars: true,
                                    foldGutter: true,
                                    drawSelection: false,
                                    syntaxHighlighting: true,
                                    bracketMatching: true,
                                }}
                            />
                        </div>

                    </div>

                )}

            </div>
        </div>
    )
}


export default SQLResultsPanel
