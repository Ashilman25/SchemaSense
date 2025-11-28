import React from 'react'
import TopNavBar from './TopNavBar'
import QueryBuilderPanel from '../panels/QueryBuilderPanel'
import SQLResultsPanel from '../panels/SQLResultsPanel'
import SchemaExplorerPanel from '../panels/SchemaExplorerPanel'


const AppLayout = () => {
  return (
    <div className = "h-screen flex flex-col bg-gray-50 dark:bg-slate-900 transition-colors">

      <TopNavBar />

      <div className = "flex-1 overflow-hidden">
        <div className = "h-full grid grid-cols-12 gap-4 p-4">

          {/* left panel */}
          <div className = "col-span-3 overflow-auto">
            <QueryBuilderPanel />
          </div>

          {/* middle panel */}
          <div className = "col-span-5 overflow-auto">
            <SQLResultsPanel />
          </div>

          {/* right panel */}
          <div className = "col-span-4 overflow-auto">
            <SchemaExplorerPanel />
          </div>

        </div>
      </div>
    </div>
  )
}

export default AppLayout
