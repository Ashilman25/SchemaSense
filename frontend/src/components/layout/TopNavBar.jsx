import React from "react";

const TopNavBar = () => {
    return (
        <nav className = "bg-white border-b border-gray-200 shadow-sm">
            <div className = "px-6 py-4 flex items-center justify-between">

                {/* left side */}
                <div className = "flex items-center space-x-3">
                    <div className = "w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                        <span className = "text-white font-bold text-lg">S</span>
                    </div>

                    <h1 className = "text-xl font-bold text-gray-800">SchemaSense</h1>
                </div>

                {/* center and right side */}
                <div className = "flex items-center space-x-4">
                    <div className = "flex items-center space-x-2 px-3 py-1.5 bg-gray-100 rounded-lg">
                        <div className = "w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className = "text-sm text-gray-600">Not Connected</span>
                    </div>


                    {/* right side */}
                    <button className = "p-2 hover:bg-gray-100 rounded-lg transition-colors" title = "Database Settings">
                        <svg className = "w-6 h-6 text-gray-600" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path 
                                strokeLinecap = "round"
                                strokeLinejoin = "round"
                                strokeWidth = {2}
                                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                            />
                            <path 
                                strokeLinecap = "round"
                                strokeLinejoin = "round"
                                strokeWidth = {2}
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                        </svg>

                    </button>

                </div>
            </div>
        </nav>
    )

}


export default TopNavBar