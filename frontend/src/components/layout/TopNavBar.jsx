import React, { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";
import DBConfigModal from "../modals/DBConfigModal";
import { dbConfigAPI } from "../../utils/api";

const TopNavBar = ({ onConnectionChange }) => {
    const {theme, toggleTheme} = useTheme();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isConnected, setIsConnected] = useState(false);


    useEffect(() => {
        checkConnectionStatus();
    }, []);

    const checkConnectionStatus = async () => {
        try {
            const response = await dbConfigAPI.getStatus();
            const connected = response.connected || false;
            setIsConnected(connected);

            if (onConnectionChange) {
                onConnectionChange(connected);
            }

        } catch (error) {
            console.error('Failed to check connection status: ', error);
            setIsConnected(false);
            if (onConnectionChange) {
                onConnectionChange(false);
            }
        }
    };

    const handleConnectionSuccess = () => {
        setIsConnected(true);
        if (onConnectionChange) {
            onConnectionChange(true);
        }
    };

    const handleOpenModal = () => {
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsModalOpen(false);
    };

    return (
        <nav className = "bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 shadow-sm transition-colors">
            <div className = "px-6 py-4 flex items-center justify-between">

                {/* left side */}
                <div className = "flex items-center space-x-3">
                    <div className = "w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                        <span className = "text-white font-bold text-lg">S</span>
                    </div>

                    <h1 className = "text-xl font-bold text-gray-800 dark:text-gray-100">SchemaSense</h1>
                </div>

                {/* center and right side */}
                <div className = "flex items-center space-x-4">

                    <div className = {`flex items-center space-x-2 px-3 py-1.5 rounded-lg ${isConnected ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-100 dark:bg-slate-700'}`}>
                        <div className = {`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                        <span className = {`text-sm ${isConnected ? 'text-green-700 dark:text-green-400' : 'text-gray-600 dark:text-gray-300'}`}>
                            {isConnected ? 'Connected' : 'Not Connected'}
                        </span>
                    </div>


                    {/* right side */}
                    <button
                        onClick={toggleTheme}
                        className = "p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        title = {theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
                    >
                        {theme === 'light' ? (
                            <svg className = "w-6 h-6 text-gray-600 dark:text-gray-300" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path
                                    strokeLinecap = "round"
                                    strokeLinejoin = "round"
                                    strokeWidth = {2}
                                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                                />
                            </svg>
                        ) : (
                            <svg className = "w-6 h-6 text-gray-600 dark:text-gray-300" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path
                                    strokeLinecap = "round"
                                    strokeLinejoin = "round"
                                    strokeWidth = {2}
                                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                                />
                            </svg>
                        )}
                    </button>

                    <button
                        onClick = {handleOpenModal}
                        className = "p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        title = "Database Settings"
                    >
                        <svg className = "w-6 h-6 text-gray-600 dark:text-gray-300" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path
                                strokeLinecap = "round"
                                strokeLinejoin = "round"
                                strokeWidth = {2}
                                d = "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                            />
                            <path
                                strokeLinecap = "round"
                                strokeLinejoin = "round"
                                strokeWidth = {2}
                                d = "M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                        </svg>
                    </button>

                </div>
            </div>


            <DBConfigModal isOpen = {isModalOpen} onClose = {handleCloseModal} onConnectionSuccess = {handleConnectionSuccess}/>
        </nav>
    )

}


export default TopNavBar