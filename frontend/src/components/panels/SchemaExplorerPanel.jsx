import React, {useState} from "react";

const SchemaExplorerPanel = () => {
    const [activeTab, setActiveTab] = useState('tables')

    return (
        <div className = "h-full bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">

            {/* tabs */}
            <div className = "border-b border-gray-200">
                <div className = "flex space-x-1 px-4">

                    <button
                        onClick = {() => setActiveTab('tables')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'tables' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600 hover:text-gray-800'
                        }`}
                    >
                        Tables
                    </button>

                    <button
                        onClick = {() => setActiveTab('er')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'er' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600 hover:text-gray-800'
                        }`}
                    >
                        ER Diagram
                    </button>
                </div>
            </div>




        </div>
    )

}


export default SchemaExplorerPanel