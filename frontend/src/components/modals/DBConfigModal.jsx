import { useState, useEffect } from 'react';
import {dbConfigAPI, schemaAPI} from '../../utils/api';
import Toast from '../common/Toast';
import { saveDBCredentials, clearDBCredentials } from '../../utils/dbStorage';

const DBConfigModal = ({ isOpen, onClose, onConnectionSuccess, currentConnection }) => {
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
  const [activeTab, setActiveTab] = useState('connection');
  const [isEditMode, setIsEditMode] = useState(false);
  const [isEditingPassword, setIsEditingPassword] = useState(false);
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState(null);

  const isConnected = currentConnection && Object.keys(currentConnection).length > 0;


  useEffect(() => {
    if (isOpen && currentConnection && Object.keys(currentConnection).length > 0) {
      setFormData({
        host: currentConnection.host || 'localhost',
        port: currentConnection.port?.toString() || '5432',
        dbname: currentConnection.dbname || '',
        user: currentConnection.user || '',
        password: currentConnection.password || ''
      });
    }

    if (isOpen) {
      setError('');
      setPingResult(null);
      setIsEditMode(false);
      setIsEditingPassword(false);
    }

  }, [isOpen, currentConnection]);

  const handleCancelEdit = () => {
    setIsEditMode(false);
    setIsEditingPassword(false);
    setError('');

    if (currentConnection) {
      setFormData({
        host: currentConnection.host || 'localhost',
        port: currentConnection.port?.toString() || '5432',
        dbname: currentConnection.dbname || '',
        user: currentConnection.user || '',
        password: currentConnection.password || ''
      });
    }

  };

  const handlePing = async () => {
    setIsPinging(true);
    setPingResult(null);
    const startTime = performance.now();

    try {
      const response = await dbConfigAPI.getStatus();
      const endTime = performance.now();
      const responseTime = Math.round(endTime - startTime);

      if (response.connected) {
        setPingResult({
          success: true,
          message: `Pinged successfully! Responded in ${responseTime}ms`,
          responseTime
        });

      } else {
        setPingResult({
          success: false,
          message: 'Connection failed. Database is not responding.',
          responseTime: null
        });
      }


    } catch (err) {
      setPingResult({
        success: false,
        message: 'Ping failed. Unable to reach database.',
        responseTime: null
      });


    } finally {
      setIsPinging(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await dbConfigAPI.disconnect();
      clearDBCredentials();

      setToast({
        type: 'success',
        message: 'Disconnected from database. Refreshing page...'
      });

      setTimeout(() => {
        window.location.reload();
      }, 800);

    } catch (err) {
      setToast({
        type: 'error',
        message: 'Failed to disconnect from database.'
      });
    }
  };
  

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleTestAndSave = async () => {
    setError('');

    if (!formData.user || !formData.password) {
      setError('Please fill in all required fields');
      return;
    }

    if (!isEditMode) {
      if (!formData.dbname) {
        setError('Please fill in all required fields');
        return;
      }

      if (!formData.port || isNaN(parseInt(formData.port))) {
        setError('Port must be a valid number');
        return;
      }
    }

    setIsConnecting(true);

    try {
      const configToSend = isEditMode
        ? {
            ...formData,
            host: currentConnection.host,
            port: currentConnection.port.toString(),
            dbname: currentConnection.dbname
          }
        : formData;

      const response = isEditMode ? await dbConfigAPI.updateCredentials(configToSend) : await dbConfigAPI.testAndSave(configToSend);

      if (response.success) {
        // Save credentials to sessionStorage for auto-reconnect
        saveDBCredentials({
          host: configToSend.host,
          port: parseInt(configToSend.port),
          dbname: configToSend.dbname,
          user: configToSend.user,
          password: configToSend.password
        });

        onConnectionSuccess();


        if (isEditMode) {
          setIsEditMode(false);
          setIsEditingPassword(false);

          setToast({
            type: 'success',
            message: 'Database credentials updated successfully.'
          });

        } else {
          onClose();
        }

      } else {
        if (isEditMode) {
          setError(`Failed to update credentials: ${response.message || 'Unable to update credentials'}. ${response.error || ''}`);

        } else {
          setError(response.message || 'Failed to connect');
        }
      }

    } catch (err) {
      if (isEditMode) {
        setError(`Failed to update credentials: ${err.message || 'An unexpected error occurred'}. Please try again.`);

      } else {
        setError(err.message || 'Failed to connect to database');
      }

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

        setFormData({
          host: response.connection.host,
          port: response.connection.port.toString(),
          dbname: response.connection.dbname,
          user: response.connection.user,
          password: response.connection.password
        });


        saveDBCredentials({
          host: response.connection.host,
          port: response.connection.port,
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
        }, 1500);

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
        <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-hidden flex">

          {/* Left Sidebar - Tabs */}
          <div className = "w-48 bg-gray-50 dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 flex flex-col">

            {/* Header for sidebar */}
            <div className = "px-4 py-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className = "text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Database
              </h2>
            </div>

            {/* Tab buttons */}
            <nav className = "flex-1 p-3 space-y-1">
              <button
                onClick = {() => {
                  setActiveTab('connection');
                  setError('');
                }}
                className = {`w-full text-left px-4 py-3 rounded-lg transition-all font-medium text-sm flex items-center space-x-3 ${
                  activeTab === 'connection'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-800'
                }`}
              >
                <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>

                <span>Connection</span>
              </button>

              <button
                onClick = {() => {
                  setActiveTab('settings');
                  setError('');
                }}
                className = {`w-full text-left px-4 py-3 rounded-lg transition-all font-medium text-sm flex items-center space-x-3 ${
                  activeTab === 'settings'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-800'
                }`}
              >
                <svg className = "w-5 h-5" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>

                <span>Settings</span>
              </button>
            </nav>
          </div>

          {/* Right Content Area */}
          <div className = "flex-1 flex flex-col max-h-[90vh]">
            {/* modal header */}
            <div className = "px-6 py-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className = "text-xl font-semibold text-gray-800 dark:text-gray-100">
                {activeTab === 'connection' ? 'Database Connection' : 'Connection Settings'}
              </h2>
            </div>

            {/* modal body */}
            <div className = "px-6 py-4 space-y-6 overflow-y-auto flex-1">

              {/* Connection Tab */}
              {activeTab === 'connection' && (
                <>
                  {isConnected ? (
                    // Show message when already connected
                    <div className = "flex flex-col items-center justify-center py-12 space-y-6">
                      <div className = "w-20 h-20 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
                        <svg className = "w-10 h-10 text-green-600 dark:text-green-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                          <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className = "text-center space-y-2">
                        <h3 className = "text-lg font-semibold text-gray-800 dark:text-gray-100">
                          Database Connected
                        </h3>
                        <p className = "text-sm text-gray-600 dark:text-gray-400 max-w-md">
                          You are currently connected to <strong>{currentConnection.dbname}</strong>
                        </p>
                      </div>

                      {/* Ping Result Display */}
                      {pingResult && (
                        <div className = {`w-full max-w-md px-4 py-3 rounded-lg border ${
                          pingResult.success
                            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                        }`}>
                          <p className = {`text-sm ${
                            pingResult.success
                              ? 'text-green-700 dark:text-green-400'
                              : 'text-red-700 dark:text-red-400'
                          }`}>
                            {pingResult.message}
                          </p>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className = "flex items-center space-x-3">
                        <button
                          onClick = {handlePing}
                          disabled = {isPinging}
                          className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                        >
                          {isPinging ? (
                            <>
                              <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                                <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                                <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              <span>Pinging...</span>
                            </>
                          ) : (
                            <>
                              <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13 10V3L4 14h7v7l9-11h-7z" />
                              </svg>
                              <span>Ping Connection</span>
                            </>
                          )}
                        </button>

                        <button
                          onClick = {handleDisconnect}
                          className = "px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center space-x-2"
                        >
                          <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                          </svg>
                          <span>Disconnect</span>
                        </button>
                      </div>

                      <p className = "text-xs text-gray-500 dark:text-gray-400 text-center max-w-md mt-2">
                        Visit the Settings tab to view or edit your connection details
                      </p>
                    </div>
                  ) : (
                    <>
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
                    </>
                  )}
                </>
              )}

              {/* Settings Tab */}
              {activeTab === 'settings' && (
                <>
                  {!isConnected ? (
                    // Show message when not connected - with min-height to prevent jumping
                    <div className = "flex flex-col items-center justify-center py-16 space-y-4 min-h-[400px]">

                      <div className = "w-20 h-20 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center">
                        <svg className = "w-10 h-10 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                          <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                        </svg>
                      </div>

                      <h3 className = "text-lg font-semibold text-gray-800 dark:text-gray-100">
                        No Database Connected
                      </h3>

                      <p className = "text-sm text-gray-600 dark:text-gray-400 text-center max-w-md">
                        Please connect to a database first. Visit the Connection tab to set up your database connection.
                      </p>
                    </div>
                  ) : (
                    // Show connection details when connected
                    <div className = "space-y-6">
                      <div className = "space-y-4">
                        <div className = "flex items-center justify-between border-b border-gray-200 dark:border-slate-700 pb-2">
                          <h3 className = "text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                            Connection Information
                          </h3>

                          {!isEditMode && (
                            <button
                              onClick = {() => setIsEditMode(true)}
                              className = "text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center space-x-1.5"
                            >
                              <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                              <span>Edit</span>
                            </button>
                          )}
                        </div>

                        {isEditMode && (
                          <div className = "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3 space-y-2">
                            <p className = "text-sm text-blue-700 dark:text-blue-400 font-medium">
                              Edit Mode Active
                            </p>

                            <p className = "text-xs text-blue-600 dark:text-blue-300">
                              You can update your username and password. These changes will be applied directly to PostgreSQL. To connect to a different database, use the Disconnect button first.
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Connection Details - Single Card Layout */}
                      <div className = "bg-gray-50 dark:bg-slate-900 rounded-lg p-5 border border-gray-200 dark:border-slate-700 space-y-4">

                        {/* Host */}
                        <div>
                          <label className = "block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
                            Host
                          </label>

                          <input
                            type = "text"
                            value = {currentConnection.host || ''}
                            readOnly = {true}
                            className = "w-full px-3 py-2 border border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 cursor-default rounded-lg"
                          />
                        </div>

                        {/* Port */}
                        <div>
                          <label className = "block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
                            Port
                          </label>

                          <input
                            type = "text"
                            value = {currentConnection.port || ''}
                            readOnly = {true}
                            className = "w-full px-3 py-2 border border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 cursor-default rounded-lg"
                          />
                        </div>

                        {/* Database Name */}
                        <div>
                          <label className = "block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
                            Database Name
                          </label>

                          <input
                            type = "text"
                            value = {currentConnection.dbname || ''}
                            readOnly = {true}
                            className = "w-full px-3 py-2 border border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 cursor-default rounded-lg"
                          />
                          {isEditMode && (
                            <p className = "text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Database name cannot be changed. Use Disconnect to connect to a different database.
                            </p>
                          )}
                        </div>

                        {/* Username */}
                        <div>
                          <label className = "block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">
                            Username
                          </label>

                          <input
                            type = "text"
                            value = {isEditMode ? formData.user : currentConnection.user || ''}
                            onChange = {(e) => setFormData(prev => ({ ...prev, user: e.target.value }))}
                            readOnly = {!isEditMode}
                            className = {`w-full px-3 py-2 border rounded-lg transition-colors ${
                              isEditMode
                                ? 'border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                                : 'border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 cursor-default'
                            }`}
                          />
                        </div>

                        {/* Password */}
                        <div>
                          <div className = "flex items-center justify-between mb-1.5">
                            <label className = "block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                              Password
                            </label>

                            {isEditMode && (
                              <button
                                type = "button"
                                onClick = {() => setIsEditingPassword(!isEditingPassword)}
                                className = "text-xs px-2 py-1 bg-gray-200 dark:bg-slate-700 hover:bg-gray-300 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-300 rounded transition-colors flex items-center space-x-1"
                              >
                                <svg className = "w-3 h-3" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>

                                <span>{isEditingPassword ? 'Hide' : 'Edit & Reveal'}</span>
                              </button>
                            )}
                          </div>
                          <div className = "relative">
                            <input
                              type = {isEditingPassword ? "text" : "password"}
                              value = {isEditingPassword ? formData.password : '••••••••••••'}
                              onChange = {(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                              readOnly = {!isEditingPassword}
                              className = {`w-full px-3 py-2 border rounded-lg transition-colors ${
                                isEditingPassword
                                  ? 'border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                                  : 'border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 cursor-default'
                              }`}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Error display for Settings tab */}
                      {error && isEditMode && (
                        <div className = "px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg space-y-2">
                          <p className = "text-sm text-red-700 dark:text-red-400 font-medium">{error}</p>
                          <p className = "text-xs text-red-600 dark:text-red-300">
                            💡 Tip: If you're switching to a completely different database, use the "Disconnect" button in the Connection tab first, then connect with new credentials.
                          </p>
                        </div>
                      )}

                      {/* Info section when not in edit mode */}
                      {!isEditMode && (
                        <div className = "px-4 py-3 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg">
                          <p className = "text-xs text-gray-600 dark:text-gray-400">
                            <strong>What you can change:</strong><br/>
                            • Username and password can be updated (changes are made in PostgreSQL)<br/>
                            • Host, port, and database name cannot be changed<br/>
                            • To connect to a different database, use "Disconnect" in Connection tab
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

            </div>

            {/* bottom buttons */}
            <div className = "px-6 py-4 border-t border-gray-200 dark:border-slate-700 flex justify-end space-x-3">
              {activeTab === 'settings' && isEditMode ? (
                <>
                  <button
                    onClick = {handleCancelEdit}
                    className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
                  >
                    Cancel Edit
                  </button>

                  <button
                    onClick = {handleTestAndSave}
                    disabled = {isConnecting}
                    className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {isConnecting ? (
                      <>
                        <svg className = "animate-spin h-4 w-4 text-white" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                          <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                          <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>

                        <span>Saving...</span>
                      </>
                    ) : (
                      <span>Save Changes</span>
                    )}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick = {onClose}
                    disabled = {isConnecting || isProvisioning}
                    className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {activeTab === 'settings' && isConnected ? 'Close' : 'Cancel'}
                  </button>

                  {activeTab === 'connection' && !isConnected && (
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
                  )}
                </>
              )}
            </div>
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
