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




                </div>









            </div>
        </nav>
    )

}


export default TopNavBar