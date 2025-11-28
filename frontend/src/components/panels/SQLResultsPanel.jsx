import React, {useState} from 'react'

const SQLResultsPanel = () => {
    const [activeTab, setActiveTab] = useState('query')

    return (
        <div className = "h-full bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">

            {/* tabs */}
            <div className = "border-b border-gray-200">
                <div className = "flex space-x-1 px-4">
                    <button
                        onClick = {() => setActiveTab('query')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'query' ? 'border-blue-500 text-blue-600': 'border-transparent text-gray-600 hover:text-gray-800'
                        }`}
                    >
                        Query SQL
                    </button>

                    <button
                        onClick = {() => setActiveTab('schema')}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === 'schema' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600 hover:text-gray-800'
                        }`}
                    >
                        Schema SQL
                    </button>
                </div>
            </div>




        </div>







    )
}


export default SQLResultsPanel