import {useState, useEffect} from 'react';
import { schemaAPI } from '../../utils/api';
import Toast from '../common/Toast';

const AddDataModal = ({isOpen, isClose}) => {
  const [activeTab, setActiveTab] = useState('manual');
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [tableMetadata, setTableMetadata] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);

  const [hasDraftData, setHasDraftData] = useState(false);
  const [showCloseConfirmation, setShowCloseConfirmation] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchTables();
      setError('');
      setShowCloseConfirmation(false);
    }
  }, [isOpen]);

  const fetchTables = async () => {
    setLoading(true);

    try {
      const schema = await schemaAPI.getSchema();

      const userTables = schema.tables.filter(table => {
        const schemaName = table.schema.toLowerCase();
        return !['pg_catalog', 'information_schema'].includes(schemaName);
      });

      setTables(userTables);

    } catch (err) {
      setError('Failed to load tables: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleTableSelect = async (tableName) => {
    setSelectedTable(tableName);

    if (!tableName) {
      setTableMetadata(null);
      return;
    }

    const table = tables.find(t => `${t.schema}.${t.name}` === tableName);

    if (table) {
      setTableMetadata(table);
    }
  };


  const handleClose = () => {
    if (hasDraftData) {
      setShowCloseConfirmation(true);
    } else {
      resetAndClose();
    }
  };

  const resetAndClose = () => {
    setActiveTab('manual');
    setSelectedTable('');
    setTableMetadata(null);
    setError('');
    setHasDraftData(false);
    setShowCloseConfirmation(false);
    onclose();
  };

  const confirmClose = () => {
    resetAndClose();
  };

  const cancelClose = () => {
    setShowCloseConfirmation(false);
  };

  if (!isOpen) return null;

  return (
    <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">

        {/* header */}
        <div className = "px-6 py-4 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className = "text-xl font-semibold text-gray-800 dark:text-gray-100">
              Add Data to Table
            </h2>

            <p className = "text-sm text-gray-600 dark:text-gray-400 mt-1">
              Insert data manually or upload from CSV/JSON files
            </p>
          </div>

          <button
            onClick = {handleClose}
            className = "p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title = "Close"
          >
            <svg className = "w-5 h-5 text-gray-500 dark:text-gray-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
              <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>


        {/* body */}
        <div className = "flex-1 overflow-y-auto px-6 py-4">

          {/* tabs */}
          <div className = "flex space-x-1 border-b border-gray-200 dark:border-slate-700 mb-6">
            <button
              onClick = {() => setActiveTab('manual')}
              className = {`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'manual'
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                }`}
            >
              Manual Entry
            </button>

            <button
              onClick = {() => setActiveTab('upload')}
              className = {`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'upload'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                }`}
            >
              Upload File
            </button>
          </div>


          {/* table selection */}
          <div className = "mb-6">
            <label className = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Table
            </label>

            {loading ? (
              <div className = "flex items-center space-x-2 text-gray-600 dark:text-gray-400">
                <svg className = "animate-spin h-4 w-4" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                  <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                  <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>

                <span className = "text-sm">Loading tables...</span>
              
              </div>

            ) : (
              <select
                value = {selectedTable}
                onChange = {(e) => handleTableSelect(e.target.value)}
                className = "w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
              >
                <option value = "">-- Choose a table --</option>

                {tables.map((table) => {
                  const fullName = `${table.schema}.${table.name}`;
                  const columnCount = table.columns?.length || 0;

                  return (
                    <option key = {fullName} value = {fullName}>
                      {fullName} ({columnCount} column{columnCount !== 1 ? 's' : ''})
                    </option>
                  );
                })}
              </select>
            )}
          </div>

          {/* column data */}
          {tableMetadata && (
              <div className = "mb-6">
                <h3 className = "text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Table Structure
                </h3>

                <div className = "bg-gray-50 dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden">
                  <table className = "w-full">

                    <thead className = "bg-gray-100 dark:bg-slate-800">
                      <tr>
                        <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                          Column
                        </th>

                        <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                          Type
                        </th>

                        <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                          Constraints
                        </th>
                      </tr>
                    </thead>

                    <tbody className = "divide-y divide-gray-200 dark:divide-slate-700">
                      {tableMetadata.columns.map((column, idx) => (
                        <tr key = {idx} className = "hover:bg-gray-50 dark:hover:bg-slate-800">
                          <td className = "px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                            {column.name}
                          </td>

                          <td className = "px-4 py-2 text-sm text-gray-600 dark:text-gray-400 font-mono">
                            {column.type}
                          </td>

                          <td className = "px-4 py-2">
                            <div className = "flex flex-wrap gap-1">
                              {column.is_pk && (
                                <span className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                                  PK
                                </span>
                              )}

                              {column.is_fk && (
                                <span className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                                  FK
                                </span>
                              )}

                              {!column.nullable && (
                                <span className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                                  Required
                                </span>
                              )}

                              {column.nullable && (
                                <span className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                                  Nullable
                                </span>
                              )}

                            </div>
                          </td>

                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* constraint warnings */}
                {(() => {
                  const requiredColumns = tableMetadata.columns.filter(col => !col.nullable && !col.is_pk);
                  const pkColumns = tableMetadata.columns.filter(col => col.is_pk);

                  if (requiredColumns.length > 0 || pkColumns.length > 0) {
                    return (
                      <div className = "mt-3 px-4 py-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <div className = "flex items-start space-x-2">
                          <svg className = "w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>

                          <div className = "flex-1">
                            <p className = "text-sm font-medium text-yellow-800 dark:text-yellow-300">
                              Important Constraints
                            </p>

                            <ul className = "mt-2 text-xs text-yellow-700 dark:text-yellow-400 space-y-1">
                              {pkColumns.length > 0 && (
                                <li>
                                  <strong>Primary Key:</strong> {pkColumns.map(c => c.name).join(', ')}
                                  {pkColumns.some(c => c.type.toLowerCase().includes('serial') || c.type.toLowerCase().includes('uuid'))
                                    ? ' (may be auto-generated)'
                                    : ' (must be provided and unique)'}
                                </li>
                              )}
                              
                              {requiredColumns.length > 0 && (
                                <li>
                                  <strong>Required Fields:</strong> {requiredColumns.map(c => c.name).join(', ')}
                                </li>
                              )}
                            </ul>
                          </div>

                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            )}


            {/* tab contents */}
            {activeTab === 'manual' && selectedTable && (
              <div className = "text-center py-8 text-gray-500 dark:text-gray-400">
                <p className = "text-sm">manual entry form later</p>
              </div> 
            )}

            {activeTab === 'upload' && selectedTable && (
              <div className = "text-center py-8 text-gray-500 dark:text-gray-400">
                <p className = "text-sm">file upload later</p>
              </div>
            )}

            {!selectedTable && !loading && (
              <div className = "text-center py-12">
                <svg className = "mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg> 

                <p className = "mt-2 text-sm text-gray-600 dark:text-gray-400">
                  Select a table to begin adding data
                </p>
              </div>
            )}

            {/* errors msg */}
            {error && (
              <div className = "px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className = "text-sm text-red-700 dark:text-red-400">{error}</p>
              </div>
            )}
        </div>




      </div>
    </div>
    
  );
};

export default AddDataModal;