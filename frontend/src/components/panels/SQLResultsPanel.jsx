import {useState, useEffect, useRef} from 'react';
import CodeMirror from '@uiw/react-codemirror';
import {sql} from '@codemirror/lang-sql';
import {oneDark} from '@codemirror/theme-one-dark';
import {useTheme} from '../../context/ThemeContext';
import {format} from 'sql-formatter';
import { sqlAPI, schemaAPI } from '../../utils/api';
import QueryPlanVisualization from '../QueryPlanVisualization';


const SQLResultsPanel = ({ generatedSql, warnings, isDbConnected, currentSchema, currentDdl, onSchemaUpdate }) => {
    const {theme} = useTheme();
    const [activeTab, setActiveTab] = useState('query');
    const [querySql, setQuerySql] = useState('-- Your generated SQL will appear here');
    const [isEditable, setIsEditable] = useState(false);

    const [queryResults, setQueryResults] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const [isDownloadMenuOpen, setIsDownloadMenuOpen] = useState(false);
    const downloadMenuRef = useRef(null);

    const [queryPlan, setQueryPlan] = useState(null);
    const [planError, setPlanError] = useState('');
    const [isPlanLoading, setIsPlanLoading] = useState(false);

    const [ddlText, setDdlText] = useState('-- Schema DDL will appear here');
    const [editedDdlText, setEditedDdlText] = useState('');
    const [isDdlLoading, setIsDdlLoading] = useState(false);
    const [isDdlApplying, setIsDdlApplying] = useState(false);
    const [notification, setNotification] = useState(null);

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

    const fetchDDL = async () => {
        setIsDdlLoading(true);

        try {
            const data = await schemaAPI.getDDL();
            setDdlText(data.ddl);
            setEditedDdlText(data.ddl);

        } catch (err) {
            console.error("Failed to fetch DDL: ", err);
            setNotification({
                type: "error",
                message: `Failed to load DDL: ${err.message || 'Unknown error'}`
            });

            setTimeout(() => setNotification(null), 5000);

        } finally {
            setIsDdlLoading(false);
        }
    };

    const handleApplyDDL = async () => {
        if (!editedDdlText.trim()) {
            setNotification({
                type: 'error',
                message: 'DDL text cannot be empty'
            });

            setTimeout(() => setNotification(null), 3000);
            return;
        }

        setIsDdlApplying(true);
        
        try {
            const response = await schemaAPI.applyDDLEdit(editedDdlText);

            if (response.success) {
                setDdlText(response.ddl);
                setEditedDdlText(response.ddl);

                if (onSchemaUpdate) {
                    onSchemaUpdate(response.schema, response.ddl);
                }

                setNotification({
                    type: 'success',
                    message: 'Schema updated from SQL'
                });

                setTimeout(() => setNotification(null), 5000);

            } else {
                const errorMsg = response.details || response.error || 'Failed to apply DDL';
                setNotification({
                    type: 'error',
                    message: errorMsg
                });

                setTimeout(() => setNotification(null), 8000);
            }

        } catch (err) {
            console.error('Failed to apply DDL: ', err);
            setNotification({
                type: 'error',
                message: `Failed to apply DDL: ${err.message || 'Unknown error'}`
            });

            setTimeout(() => setNotification(null), 8000);

        } finally {
            setIsDdlApplying(false);
        }
    };


    //when sql tab is open and no DDL yet, or when DDL updates from undo/redo
    useEffect(() => {
        if (activeTab === 'schema' && isDbConnected) {
            if (currentDdl) {
                setDdlText(currentDdl);
                setEditedDdlText(currentDdl);

            } else if (!ddlText.startsWith('CREATE')) {
                fetchDDL();
            }
        }
    }, [activeTab, isDbConnected, currentDdl]);


    //outside clicks to close download menu
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (downloadMenuRef.current && !downloadMenuRef.current.contains(event.target)) {
                setIsDownloadMenuOpen(false);
            }
        };

        const handleEscape = (event) => {
            if (event.key === 'Escape') {
                setIsDownloadMenuOpen(false);
            }
        };

        if (isDownloadMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            document.addEventListener('keydown', handleEscape);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, [isDownloadMenuOpen]);

    const handleDownloadJSON = () => {
        console.log('Download JSON');
        setIsDownloadMenuOpen(false);
    };

    const handleDownloadCSV = () => {
        console.log('Download CSV');
        setIsDownloadMenuOpen(false);
    };

    const handleDownloadPDF = () => {
        console.log('Download PDF');
        setIsDownloadMenuOpen(false);
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
                                onClick = {handleExecuteQuery}
                                disabled = {isLoading}
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
                                <div className = "m-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                    <div className = "flex items-start">
                                        <svg className = "h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 mr-3" fill = "currentColor" viewBox = "0 0 20 20">
                                            <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
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
                                    <div className = "px-4 py-3 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between bg-white dark:bg-slate-800">

                                        <div className = "flex items-center space-x-4">
                                            <span className = "text-sm font-medium text-gray-700 dark:text-gray-300">
                                                Row count: <span className = "text-blue-600 dark:text-blue-400">{queryResults.row_count}</span>
                                            </span>

                                            {queryResults.truncated && (
                                                <span className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800">
                                                    Results truncated to {queryResults.row_count} rows
                                                </span>
                                            )}
                                        </div>

                                        {/* download button + menu */}
                                        <div className = "relative" ref = {downloadMenuRef}>

                                            <button
                                                onClick = {() => setIsDownloadMenuOpen(!isDownloadMenuOpen)}
                                                disabled = {!queryResults.rows || queryResults.rows.length === 0}
                                                className = {`
                                                    flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                                                    ${queryResults.rows && queryResults.rows.length > 0
                                                        ? 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white'
                                                        : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                                                    }
                                                `}
                                                aria-expanded = {isDownloadMenuOpen}
                                                aria-haspopup = "true"
                                            >
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                </svg>

                                                <span>Download</span>

                                                <svg className = {`w-4 h-4 transition-transform ${isDownloadMenuOpen ? 'rotate-180' : ''}`} fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 9l-7 7-7-7" />
                                                </svg>
                                            </button>

                                            {/* the menu itself */}
                                            {isDownloadMenuOpen && queryResults.rows && queryResults.rows.length > 0 && (
                                                <div
                                                    className = "absolute right-0 mt-2 w-48 rounded-lg shadow-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 py-1 z-10"
                                                    role = "menu"
                                                    aria-orientation = "vertical"
                                                >
                                                    <button
                                                        onClick = {handleDownloadJSON}
                                                        onKeyDown = {(e) => {
                                                            if (e.key === 'Enter' || e.key === ' ') {
                                                                e.preventDefault();
                                                                handleDownloadJSON();
                                                            }
                                                        }}
                                                        className = "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 focus:bg-gray-100 dark:focus:bg-slate-700 focus:outline-none flex items-center space-x-2 transition-colors"
                                                        role = "menuitem"
                                                        tabIndex = {0}
                                                    >

                                                        <svg className = "w-4 h-4" viewBox = "0 0 24 24" fill = "none" stroke = "currentColor" xmlns = "http://www.w3.org/2000/svg">
                                                            <g fill = "none" stroke = "currentColor" strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = "2">
                                                                <path d = "M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                                                                <path d = "M14 2v6h6m-10 4a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1a1 1 0 0 1 1 1v1a1 1 0 0 0 1 1m4 0a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1a1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1" />
                                                            </g>                                                        
                                                        </svg>


                                                        <span>Download as JSON</span>
                                                    </button>

                                                    <button
                                                        onClick = {handleDownloadCSV}
                                                        onKeyDown = {(e) => {
                                                            if (e.key === 'Enter' || e.key === ' ') {
                                                                e.preventDefault();
                                                                handleDownloadCSV();
                                                            }
                                                        }}
                                                        className = "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 focus:bg-gray-100 dark:focus:bg-slate-700 focus:outline-none flex items-center space-x-2 transition-colors"
                                                        role = "menuitem"
                                                        tabIndex = {0}
                                                    >
                                                        <svg className = "w-4 h-4" viewBox = "0 0 16 16" xmlns = "http://www.w3.org/2000/svg">
                                                            <path fill = "currentColor" fillRule = "evenodd" clipRule = "evenodd" d = "M1.5 1.5A.5.5 0 0 1 2 1h6.5a.5.5 0 0 1 .354.146l2.5 2.5A.5.5 0 0 1 11.5 4v2h-1V5H8a.5.5 0 0 1-.5-.5V2h-5v12h8v-.5h1v1a.5.5 0 0 1-.5.5H2a.5.5 0 0 1-.5-.5zm7 .707V4h1.793zm2.55 5.216A3 3 0 0 1 11 7h1q-.001.004.007.069q.01.07.029.182c.026.15.063.34.11.56c.092.44.216.982.34 1.512s.25 1.043.343 1.425l.062.252h.218l.062-.252c.093-.382.218-.896.342-1.425c.125-.53.249-1.072.341-1.512c.047-.22.085-.41.11-.56q.02-.111.029-.182L14 7h1c0 .113-.024.272-.05.423c-.03.165-.07.369-.117.594a70 70 0 0 1-.346 1.535a167 167 0 0 1-.459 1.895l-.043.174A.5.5 0 0 1 13.5 12h-1a.5.5 0 0 1-.485-.379l-.043-.174a192 192 0 0 1-.459-1.895a70 70 0 0 1-.346-1.535a18 18 0 0 1-.117-.594M4 8a1 1 0 0 1 1-1h2v1H5v3h2v1H5a1 1 0 0 1-1-1zm3.5 0a1 1 0 0 1 1-1h2v1h-2v1h1a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1h-2v-1h2v-1h-1a1 1 0 0 1-1-1z" />
                                                        </svg>

                                                        <span>Download as CSV</span>
                                                    </button>

                                                    <button
                                                        onClick = {handleDownloadPDF}
                                                        onKeyDown = {(e) => {
                                                            if (e.key === 'Enter' || e.key === ' ') {
                                                                e.preventDefault();
                                                                handleDownloadPDF();
                                                            }
                                                        }}
                                                        className = "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 focus:bg-gray-100 dark:focus:bg-slate-700 focus:outline-none flex items-center space-x-2 transition-colors"
                                                        role = "menuitem"
                                                        tabIndex = {0}
                                                    >
                                                        <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                        </svg>

                                                        <span>Download as PDF</span>
                                                    </button>
                                                </div>
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
                    <div className = "h-full flex flex-col">
                        {!isDbConnected ? (
                            <div className = "flex flex-col items-center justify-center h-full py-8 px-4 text-center">
                                <svg className = "w-12 h-12 text-gray-400 dark:text-gray-500 mb-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth={2} d = "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                                </svg>
                                <p className = "text-sm text-gray-600 dark:text-gray-400 mb-2">
                                    No database connected
                                </p>
                                <p className = "text-xs text-gray-500 dark:text-gray-500">
                                    Click the settings icon in the top right to connect to a database
                                </p>
                            </div>
                        ) : (
                            <>
                                {/* Notification banner */}
                                {notification && (
                                    <div className = {`mb-4 p-3 ${
                                        notification.type === 'success'
                                            ? 'bg-green-100 dark:bg-green-900/30 border border-green-200 dark:border-green-800'
                                            : 'bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800'
                                    } rounded-lg`}>
                                        <div className = "flex items-center justify-between">
                                            <div className = "flex items-center space-x-2">
                                                {notification.type === 'success' ? (
                                                    <svg className = "w-5 h-5 text-green-600 dark:text-green-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                ) : (
                                                    <svg className = "w-5 h-5 text-red-600 dark:text-red-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                )}
                                                <span className = {`text-sm font-medium ${
                                                    notification.type === 'success'
                                                        ? 'text-green-800 dark:text-green-200'
                                                        : 'text-red-800 dark:text-red-200'
                                                }`}>
                                                    {notification.message}
                                                </span>
                                            </div>
                                            <button
                                                onClick = {() => setNotification(null)}
                                                className = {`${
                                                    notification.type === 'success'
                                                        ? 'text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300'
                                                        : 'text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300'
                                                }`}
                                            >
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* Info note */}
                                <div className = "mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                                    <div className = "flex items-start space-x-2">
                                        <svg className = "w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <p className = "text-xs text-blue-800 dark:text-blue-200">
                                            Editing this DDL updates the in-app schema model only. It does not change the live database by default.
                                        </p>
                                    </div>
                                </div>

                                {/* DDL Editor */}
                                <div className = "flex-1 min-h-[300px] rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                                    {isDdlLoading ? (
                                        <div className = "flex items-center justify-center h-full bg-gray-50 dark:bg-slate-900">
                                            <div className = "text-center">
                                                <svg className = "animate-spin h-8 w-8 text-blue-600 dark:text-blue-400 mx-auto mb-4" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                                    <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                                    <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                <p className = "text-sm text-gray-600 dark:text-gray-400">Loading DDL...</p>
                                            </div>
                                        </div>
                                    ) : (
                                        <CodeMirror
                                            value = {editedDdlText}
                                            height = "100%"
                                            minHeight = "300px"
                                            extensions = {[sql()]}
                                            onChange = {(value) => setEditedDdlText(value)}
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
                                    )}
                                </div>

                                {/* CTAs */}
                                <div className = "mt-4 flex items-center justify-between">
                                    <button
                                        onClick = {handleApplyDDL}
                                        disabled = {isDdlApplying || isDdlLoading}
                                        className = {`
                                            bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600
                                            text-white font-medium py-2 px-4 rounded-lg transition-colors
                                            flex items-center space-x-2
                                            ${isDdlApplying || isDdlLoading ? 'opacity-50 cursor-not-allowed' : ''}
                                        `}
                                    >
                                        {isDdlApplying && (
                                            <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                                <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                                <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                        )}
                                        <span>{isDdlApplying ? 'Applying...' : 'Apply to Model'}</span>
                                    </button>

                                    <div className = "flex items-center space-x-2">
                                        <button
                                            onClick = {fetchDDL}
                                            disabled = {isDdlLoading || isDdlApplying}
                                            className = {`
                                                flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors
                                                ${isDdlLoading || isDdlApplying
                                                    ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                                                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-800 dark:hover:text-gray-200'
                                                }
                                            `}
                                            title = "Refresh DDL from current schema"
                                        >
                                            {isDdlLoading ? (
                                                <svg className = "animate-spin h-4 w-4" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                                    <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                                    <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                            ) : (
                                                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                </svg>
                                            )}
                                            <span className = "text-sm font-medium">Refresh</span>
                                        </button>

                                        <button
                                            onClick = {() => setEditedDdlText(ddlText)}
                                            disabled = {isDdlLoading || isDdlApplying || editedDdlText === ddlText}
                                            className = {`
                                                text-sm px-3 py-2 rounded-lg transition-colors
                                                ${isDdlLoading || isDdlApplying || editedDdlText === ddlText
                                                    ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                                                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-800 dark:hover:text-gray-200'
                                                }
                                            `}
                                            title = "Discard edits and reset to last saved DDL"
                                        >
                                            Reset
                                        </button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                )}

            </div>
        </div>
    )
}


export default SQLResultsPanel
