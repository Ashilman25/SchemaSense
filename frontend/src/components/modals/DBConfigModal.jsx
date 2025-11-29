import React, { useState } from 'react';
import {dbConfigAPI} from '../../utils/api';

const DBConfigModal = ({ isOpen, onClose, onConnectionSuccess }) => {
  const [formData, setFormData] = useState({
    host: 'localhost',
    port: '5432',
    dbname: '',
    user: '',
    password: ''
  });

  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleTestAndSave = async () => {
    setError('');
    setIsLoading(true);

    try {
      const response = await dbConfigAPI.testAndSave(formData);

      if (response.success) {
        onConnectionSuccess();
        onClose();
      } else {
        setError(response.message || 'Failed to connect');
      }

    } catch (err) {
      setError(err.message || 'Failed to connect to database');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md mx-4">

        {/* modal header */}
        <div className = "px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <h2 className = "text-xl font-semibold text-gray-800 dark:text-gray-100">
            Database Connection
          </h2>
        </div>

        {/* modal body */}
        <div className = "px-6 py-4 space-y-4">

          {/* host */}
          <div>
            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Host
            </label>

            <input
              type = "text"
              name = "host"
              value = {formData.host}
              onChange = {handleChange}
              className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              placeholder = "localhost"
            />
          </div>

          {/* port */}
          <div>
            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Port
            </label>

            <input 
              type = "text"
              name = "port"
              value = {formData.port}
              onChange = {handleChange}
              className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              placeholder = "5432"
            />
          </div>

          {/* db name */}
          <div>
            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Database Name
            </label>

            <input 
              type = "text"
              name = "dbname"
              value = {formData.dbname}
              onChange = {handleChange}
              className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              placeholder = "mydb"
            />
          </div>

          {/* username */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Username
            </label>

            <input
              type = "text"
              name = "user"
              value = {formData.user}
              onChange = {handleChange}
              className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              placeholder = "postgres"
            />
          </div>

          {/* password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Password
            </label>

            <input
              type = "password"
              name = "password"
              value = {formData.password}
              onChange = {handleChange}
              className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              placeholder = "••••••••"
            />
          </div>

          {/* error msgs */}
          {error && (
            <div className = "px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className = "text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* bottom buttons */}
        <div className = "px-6 py-4 border-t border-gray-200 dark:border-slate-700 flex justify-end space-x-3">
          <button 
            onClick = {onClose}
            disabled = {isLoading}
            className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          
          >
            Cancel
          </button>

          <button
            onClick = {handleTestAndSave}
            disabled = {isLoading}
            className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isLoading ? (
              <>
                <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                  <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                  <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>

                <span>Testing...</span>
              </>
            ) : (
              <span>Test & Save</span>
            )}
          </button>
        </div>


      </div>
    </div>
  );
};

export default DBConfigModal;
