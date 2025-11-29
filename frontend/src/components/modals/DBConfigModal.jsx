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



        </div>





      </div>
    </div>
  );
};

export default DBConfigModal;
