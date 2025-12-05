import { useState } from 'react';
import {dbConfigAPI, schemaAPI} from '../../utils/api';
import Toast from '../common/Toast';

const DBConfigModal = ({ isOpen, onClose, onConnectionSuccess }) => {
  const [formData, setFormData] = useState({
    host: 'localhost',
    port: '5432',
    dbname: '',
    user: '',
    password: ''
  });

  const [loadSampleData, setLoadSampleData] = useState(false);
  const [error, setError] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [toast, setToast] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleTestAndSave = async () => {
    setError('');

    if (!formData.dbname || !formData.user || !formData.password) {
      setError('Please fill in all required fields');
      return;
    }

    if (!formData.port || isNaN(parseInt(formData.port))) {
      setError('Port must be a valid number');
      return;
    }

    setIsConnecting(true);

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
      setIsConnecting(false);
    }
  };

  const handleProvision = async () => {
    setError('');
    setIsProvisioning(true);

    try {
      const response = await dbConfigAPI.provision(loadSampleData);

      if (response.success && response.connection) {
        // Populate the form fields with the provisioned database credentials
        setFormData({
          host: response.connection.host,
          port: response.connection.port.toString(),
          dbname: response.connection.dbname,
          user: response.connection.user,
          password: response.connection.password
        });

        onConnectionSuccess();

        setToast({
          type: 'success',
          message: 'SchemaSense-managed Postgres created and connected.'
        });

        try {
          await schemaAPI.getSchema();

        } catch (schemaErr) {
          console.warn('Schema refresh failed, but connection succeeded:', schemaErr);
        }

        // Auto-close modal after a brief delay
        setTimeout(() => {
          onClose();
        }, 1000);

      } else {
        setError(response.message || 'Failed to provision database');
      }

    } catch (err) {
      if (err.message && err.message.includes('429')) {
        setError("You've reached the limit of demo databases. Please reuse your existing one or try again later.");

      } else if (err.message && err.message.includes('quota_exceeded')) {
        setError("You've reached the limit of demo databases. Please reuse your existing one or try again later.");

      } else if (err.message && err.message.includes('provision_failed')) {
        setError("We couldn't create a demo database right now. Please try again in a bit.");

      } else {
        setError(err.message || 'Failed to provision database');
      }

    } finally {
      setIsProvisioning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">

          {/* modal header */}
          <div className = "px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <h2 className = "text-xl font-semibold text-gray-800 dark:text-gray-100">
              Database Connection
            </h2>
          </div>

          {/* modal body */}
          <div className = "px-6 py-4 space-y-6">

            {/* SchemaSense-Managed Postgres Section */}
            <div className = "space-y-4">
              <div className = "border-b border-gray-200 dark:border-slate-700 pb-2">
                <h3 className = "text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  Quick Start
                </h3>
              </div>

              <div className = "space-y-3">
                <div className = "text-sm text-gray-600 dark:text-gray-400 space-y-2">
                  <p>
                    Create an <strong>empty demo database</strong> hosted for you. Perfect for trying out SchemaSense!
                  </p>

                  <ul className = "list-disc list-inside space-y-1 text-xs">
                    <li>Not production-grade storage</li>
                    <li>May be temporary and cleaned up after inactivity</li>
                    <li>Read-only from the app's perspective</li>
                  </ul>
                </div>

                {/* Load Sample Data Toggle */}
                <div className = "flex items-center space-x-3 py-2">
                  <input
                    type = "checkbox"
                    id = "loadSampleData"
                    checked = {loadSampleData}
                    onChange = {(e) => setLoadSampleData(e.target.checked)}
                    disabled = {isProvisioning}
                    className = "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  />

                  <label htmlFor = "loadSampleData" className = "text-sm font-medium text-gray-700 dark:text-gray-300">
                    Load demo sales data
                  </label>
                </div>

                {/* Provision Button */}
                <button
                  onClick = {handleProvision}
                  disabled = {isProvisioning || isConnecting}
                  className = "w-full px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 shadow-sm"
                >
                  {isProvisioning ? (
                    <>
                      <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                        <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                        <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>

                      <span>Provisioning...</span>
                    </>
                  ) : (
                    <>
                      <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>

                      <span>Create SchemaSense-managed Database</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* divider */}
            <div className = "relative">
              <div className = "absolute inset-0 flex items-center">
                <div className = "w-full border-t border-gray-300 dark:border-slate-600"></div>
              </div>
              
              <div className = "relative flex justify-center text-sm">
                <span className = "px-2 bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400">
                  Or connect to your own database
                </span>
              </div>
            </div>

            {/* Manual Connection Section */}
            <div className = "space-y-4">
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
                  disabled = {isProvisioning}
                  className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  disabled = {isProvisioning}
                  className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  disabled = {isProvisioning}
                  className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  disabled = {isProvisioning}
                  className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  placeholder = "postgres"
                />
              </div>

              {/* password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Password
                </label>

                <div className="relative">
                  <input
                    type = {showPassword ? "text" : "password"}
                    name = "password"
                    value = {formData.password}
                    onChange = {handleChange}
                    disabled = {isProvisioning}
                    className = "w-full px-3 py-2 pr-10 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    placeholder = "••••••••"
                  />
                  <button
                    type = "button"
                    onClick = {() => setShowPassword(!showPassword)}
                    className = "absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    tabIndex = {-1}
                  >
                    {showPassword ? (
                      //hide password
                      <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      //show password
                      <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>

              </div>
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
              disabled = {isConnecting || isProvisioning}
              className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"

            >
              Cancel
            </button>

            <button
              onClick = {handleTestAndSave}
              disabled = {isConnecting || isProvisioning}
              className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {isConnecting ? (
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

      {toast && (
        <Toast
          message = {toast.message}
          type = {toast.type}
          duration = {3000}
          onClose = {() => setToast(null)}
        />
      )}
    </>
  );
};

export default DBConfigModal;
