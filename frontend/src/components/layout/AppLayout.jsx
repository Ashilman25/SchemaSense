import {useState, useCallback} from 'react'
import TopNavBar from './TopNavBar'
import QueryBuilderPanel from '../panels/QueryBuilderPanel'
import SQLResultsPanel from '../panels/SQLResultsPanel'
import SchemaExplorerPanel from '../panels/SchemaExplorerPanel'


const AppLayout = () => {
  const [generatedSql, setGeneratedSql] = useState('');
  const [sqlWarnings, setSqlWarnings] = useState([]);
  const [nlQuestion, setNlQuestion] = useState('');

  const [isDbConnected, setIsDbConnected] = useState(false);
  const [shouldRefreshSchema, setShouldRefreshSchema] = useState(0);

  const [currentSchema, setCurrentSchema] = useState(null);
  const [currentDdl, setCurrentDdl] = useState(null);
  const [schemaUpdateCallback, setSchemaUpdateCallback] = useState(null);

  const handleSqlGenerated = (sql, warnings = []) => {
    setGeneratedSql(sql);
    setSqlWarnings(warnings);
  };

  const handleQuestionChange = (question) => {
    setNlQuestion(question);
  };

  const handleAskAboutTable = (tableName) => {
    setNlQuestion(`Show me some basic information from ${tableName}`);
  };

  const handleDbConnectionChange = (connected) => {
    setIsDbConnected(connected);
    if (connected) {
      setShouldRefreshSchema(prev => prev + 1);
    }
  };

  const handleSchemaChange = useCallback((newSchema, newDdl) => {
    setCurrentSchema(newSchema);
    setCurrentDdl(newDdl);
  }, []);

  const handleSchemaUpdateCallbackRegister = useCallback((callback) => {
    setSchemaUpdateCallback(() => callback);
  }, []);

  return (
    <div className = "h-screen flex flex-col bg-gray-50 dark:bg-slate-900 transition-colors">

      <TopNavBar onConnectionChange = {handleDbConnectionChange} />

      <div className = "flex-1 overflow-hidden">
        <div className = "h-full grid grid-cols-12 gap-4 p-4">

          {/* left panel */}
          <div className = "col-span-3 overflow-auto">
            <QueryBuilderPanel
              onSqlGenerated = {handleSqlGenerated}
              question = {nlQuestion}
              onQuestionChange = {handleQuestionChange}
              isDbConnected = {isDbConnected}
            />
          </div>

          {/* middle panel */}
          <div className = "col-span-5 overflow-auto">
            <SQLResultsPanel
              generatedSql = {generatedSql}
              warnings = {sqlWarnings}
              isDbConnected = {isDbConnected}
              currentSchema = {currentSchema}
              currentDdl = {currentDdl}
              onSchemaUpdate = {schemaUpdateCallback}
            />
          </div>

          {/* right panel */}
          <div className = "col-span-4 overflow-auto">
            <SchemaExplorerPanel
              onAskAboutTable = {handleAskAboutTable}
              isDbConnected = {isDbConnected}
              refreshTrigger = {shouldRefreshSchema}
              onSchemaChange = {handleSchemaChange}
              onRegisterUpdateCallback = {handleSchemaUpdateCallbackRegister}
            />
          </div>

        </div>
      </div>
    </div>
  )
}

export default AppLayout
