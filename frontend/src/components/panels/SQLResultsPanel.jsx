import {useState, useEffect} from 'react';
import CodeMirror from '@uiw/react-codemirror';
import {sql} from '@codemirror/lang-sql';
import {oneDark} from '@codemirror/theme-one-dark';
import {useTheme} from '../../context/ThemeContext';

const SQLResultsPanel = ({ generatedSql, warnings }) => {
    const {theme} = useTheme();
    const [activeTab, setActiveTab] = useState('query');
    const [querySql, setQuerySql] = useState('-- Your generated SQL will appear here');
    const [schemaSql, setSchemaSql] = useState('-- Schema DDL will appear here once connected');
    const [isEditable, setIsEditable] = useState(false);

    useEffect(() => {
        if (generatedSql) {
            setQuerySql(generatedSql);
        }
    }, [generatedSql]);

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
                            <button className = "bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                                Run Query
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

                        {/* results */}
                        <div className = "mt-4 flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-600 p-4 transition-colors">
                            <div className = "text-sm text-gray-500 dark:text-gray-400">
                                Query results will appear here
                            </div>
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