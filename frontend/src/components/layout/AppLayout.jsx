import React from 'react'


const AppLayout = () => {
  return (
    <div className = "h-screen flex flex-col bg-gray-50">

      <p>nav bar</p>

      <div className = "flex-1 overflow-hidden">
        <div className = "h-full grid grid-cols-12 gap-4 p-4">

          {/* left panel */}
          <div className = "col-span-3 overflow-auto">
            <p>quey builder panel</p>
          </div>

          {/* middle panel */}
          <div className = "col-span-5 overflow-auto">
            <p>sql results panel</p>
          </div>

          {/* right panel */}
          <div className = "col-span-4 overflow-auto">
            <p>schema panel</p>
          </div>

        </div>
      </div>
    </div>
  )
}

export default AppLayout
