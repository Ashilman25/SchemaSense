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









            </div>
        </nav>
    )

}


export default TopNavBar