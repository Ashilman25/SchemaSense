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




        </div>




      </div>
    </div>
    
  );
};

export default AddDataModal;