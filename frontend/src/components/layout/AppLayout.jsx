import {useState, useCallback, useRef, useEffect} from 'react'
import TopNavBar from './TopNavBar'
import QueryBuilderPanel from '../panels/QueryBuilderPanel'
import SQLResultsPanel from '../panels/SQLResultsPanel'
import SchemaExplorerPanel from '../panels/SchemaExplorerPanel'


const AppLayout = () => {
  const containerRef = useRef(null)
  const dragStateRef = useRef(null)

  const [generatedSql, setGeneratedSql] = useState('');
  const [sqlWarnings, setSqlWarnings] = useState([]);
  const [nlQuestion, setNlQuestion] = useState('');

  const [isDbConnected, setIsDbConnected] = useState(false);
  const [shouldRefreshSchema, setShouldRefreshSchema] = useState(0);

  const [currentSchema, setCurrentSchema] = useState(null);
  const [currentDdl, setCurrentDdl] = useState(null);
  const [schemaUpdateCallback, setSchemaUpdateCallback] = useState(null);

  const [panelWidths, setPanelWidths] = useState({
    left: 25,
    middle: 42,
    right: 33
  });
  const [activeHandle, setActiveHandle] = useState(null);

  const MIN_LEFT_WIDTH = 220;
  const MIN_MIDDLE_WIDTH = 360;
  const MIN_RIGHT_WIDTH = 260;

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

  const stopHorizontalDrag = useCallback(() => {
    if (!dragStateRef.current) return;

    document.removeEventListener('mousemove', handleHorizontalDrag);
    document.removeEventListener('mouseup', stopHorizontalDrag);
    document.body.style.userSelect = '';

    dragStateRef.current = null;
    setActiveHandle(null);
  }, []);

  const handleHorizontalDrag = useCallback((event) => {
    const dragState = dragStateRef.current;
    if (!dragState || !containerRef.current) return;

    const {type, startX, containerWidth, leftPx, rightPx} = dragState;
    const deltaX = event.clientX - startX;

    let newLeft = leftPx;
    let newRight = rightPx;
    const minTotalMiddle = MIN_MIDDLE_WIDTH;

    if (type === 'left') {
      const availableForLeftMiddle = containerWidth - rightPx;
      const maxLeft = Math.max(availableForLeftMiddle - minTotalMiddle, MIN_LEFT_WIDTH);
      newLeft = Math.min(Math.max(leftPx + deltaX, MIN_LEFT_WIDTH), maxLeft);

    } else if (type === 'right') {
      const availableForMiddleRight = containerWidth - leftPx;
      const maxRight = Math.max(availableForMiddleRight - minTotalMiddle, MIN_RIGHT_WIDTH);
      newRight = Math.min(Math.max(rightPx - deltaX, MIN_RIGHT_WIDTH), maxRight);
    }

    const middleWidth = Math.max(containerWidth - newLeft - newRight, 0);

    const updated = {
      left: (newLeft / containerWidth) * 100,
      middle: (middleWidth / containerWidth) * 100,
      right: (newRight / containerWidth) * 100
    };

    setPanelWidths(updated);
  }, []);

  const startHorizontalDrag = (type, event) => {
    if (!containerRef.current) return;
    event.preventDefault();
    const bounds = containerRef.current.getBoundingClientRect();
    const containerWidth = bounds.width;

    if (containerWidth <= 0) return;

    const leftPx = (panelWidths.left / 100) * containerWidth;
    const rightPx = (panelWidths.right / 100) * containerWidth;

    dragStateRef.current = {
      type,
      startX: event.clientX,
      containerWidth,
      leftPx,
      rightPx
    };

    document.body.style.userSelect = 'none';
    setActiveHandle(type);

    document.addEventListener('mousemove', handleHorizontalDrag);
    document.addEventListener('mouseup', stopHorizontalDrag);
  };

  useEffect(() => {
    return () => {
      stopHorizontalDrag();
    };
  }, [stopHorizontalDrag]);

  return (
    <div className = "h-screen flex flex-col bg-gray-50 dark:bg-slate-900 transition-colors">

      <TopNavBar onConnectionChange = {handleDbConnectionChange} />

      <div className = "flex-1 overflow-hidden">
        <div className = "h-full p-4 overflow-hidden">
          <div ref = {containerRef} className = "relative h-full flex gap-4 overflow-hidden">

            {/* left panel */}
            <div
              className = "relative h-full overflow-y-auto overflow-x-hidden"
              style = {{flexBasis: `${panelWidths.left}%`, flexGrow: 0, flexShrink: 1, minWidth: MIN_LEFT_WIDTH}}
            >
              <QueryBuilderPanel
                onSqlGenerated = {handleSqlGenerated}
                question = {nlQuestion}
                onQuestionChange = {handleQuestionChange}
                isDbConnected = {isDbConnected}
              />

              <div
                className = {`absolute top-0 right-[-6px] h-full w-2.5 cursor-col-resize z-20 transition-colors ${activeHandle === 'left' ? 'bg-blue-500/10' : 'hover:bg-blue-500/10'}`}
                onMouseDown = {(e) => startHorizontalDrag('left', e)}
              />
            </div>

            {/* middle panel */}
            <div
              className = "relative h-full overflow-y-auto overflow-x-hidden"
              style = {{flexBasis: `${panelWidths.middle}%`, flexGrow: 0, flexShrink: 1, minWidth: MIN_MIDDLE_WIDTH}}
            >
              <SQLResultsPanel
                generatedSql = {generatedSql}
                warnings = {sqlWarnings}
                isDbConnected = {isDbConnected}
                currentSchema = {currentSchema}
                currentDdl = {currentDdl}
                onSchemaUpdate = {schemaUpdateCallback}
              />

              <div
                className = {`absolute top-0 right-[-6px] h-full w-2.5 cursor-col-resize z-20 transition-colors ${activeHandle === 'right' ? 'bg-blue-500/10' : 'hover:bg-blue-500/10'}`}
                onMouseDown = {(e) => startHorizontalDrag('right', e)}
              />
            </div>

            {/* right panel */}
            <div
              className = "relative h-full overflow-y-auto overflow-x-hidden"
              style = {{flexBasis: `${panelWidths.right}%`, flexGrow: 0, flexShrink: 1, minWidth: MIN_RIGHT_WIDTH}}
            >
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
    </div>
  )
}

export default AppLayout
