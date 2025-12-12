import {useState, useEffect, useRef} from 'react';
import { schemaAPI, dataAPI } from '../../utils/api';
import Toast from '../common/Toast';
import {
  parseCSV,
  parseJSON,
  validateFileSize,
  validateFileType,
  autoMatchColumns,
  validateColumnMapping,
  applyColumnMapping,
  MAX_FILE_SIZE,
  MAX_ROWS
} from '../../utils/fileParser';

const AddDataModal = ({isOpen, onClose}) => {
  const [activeTab, setActiveTab] = useState('manual');
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [tableMetadata, setTableMetadata] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);

  const [hasDraftData, setHasDraftData] = useState(false);
  const [showCloseConfirmation, setShowCloseConfirmation] = useState(false);
  const [showInsertConfirmation, setShowInsertConfirmation] = useState(false);
  const [isInserting, setIsInserting] = useState(false);

  const [rows, setRows] = useState([]);
  const [validationErrors, setValidationErrors] = useState({});


  const fileInputRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadStep, setUploadStep] = useState('select'); // select, mapping, preview
  const [parsedData, setParsedData] = useState(null);
  const [columnMapping, setColumnMapping] = useState({});
  const [mappingValidation, setMappingValidation] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

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
      setRows([]);
      setValidationErrors({});
      return;
    }

    const table = tables.find(t => `${t.schema}.${t.name}` === tableName);

    if (table) {
      setTableMetadata(table);
      initializeRows(table);
    }
  };



  const initializeRows = (table) => {
    const emptyRow = {};

    table.columns.forEach(col => {
      emptyRow[col.name] = '';
    });

    setRows([emptyRow]);
    setValidationErrors({});
    setHasDraftData(false);
  };


  //validation funcs
  const validateValue = (value, column) => {
    const type = column.type.toLowerCase();

    if (value === '' || value === null || value === undefined) {
      if (!column.nullable && !column.is_pk) {
        return 'Required field';
      }
      return null;
    }
    
    if (type.includes('int') || type.includes('serial')) {
      if (!/^-?\d+$/.test(value)) {
        return 'Must be an integer';
      }

    } else if (type.includes('numeric') || type.includes('decimal') || type.includes('float') || type.includes('double')) {
      if (!/^-?\d+\.?\d*$/.test(value)) {
        return 'Must be a number';
      }

    } else if (type.includes('bool')) {
      const validBool = ['true', 'false', 't', 'f', '1', '0', 'yes', 'no', 'y', 'n'];
      if (!validBool.includes(value.toLowerCase())) {
        return 'Must be true/false, 1/0, yes/no, or y/n';
      }

    } else if (type.includes('date') && !type.includes('timestamp')) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        return 'Must be YYYY-MM-DD format';
      }

    } else if (type.includes('timestamp') || type.includes('datetime')) {
      if (!/^\d{4}-\d{2}-\d{2}/.test(value)) {
        return 'Must start with YYYY-MM-DD';
      }

    } else if (type.includes('uuid')) {
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
        return 'Must be a valid UUID (e.g., 123e4567-e89b-12d3-a456-426614174000)';
      }

    } else if (type.includes('json')) {
      try {
        JSON.parse(value);
      } catch {
        return 'Must be valid JSON';
      }
    }

    return null; //valid
  };


  const validateRow = (rowIndex) => {
    if (!tableMetadata) return {};

    const row = rows[rowIndex];
    const errors = {};

    tableMetadata.columns.forEach(col => {
      const value = row[col.name];
      const error = validateValue(value, col);

      if (error) {
        errors[col.name] = error;
      }
    });

    return errors;
  };


  const validateAllRows = () => {
    const allErrors = {};

    // First, validate each row individually
    rows.forEach((_, idx) => {
      const rowErrors = validateRow(idx);

      if (Object.keys(rowErrors).length > 0) {
        allErrors[idx] = rowErrors;
      }
    });

    if (tableMetadata) {
      const pkColumns = tableMetadata.columns.filter(col => col.is_pk);

      pkColumns.forEach(pkCol => {
        const valueMap = new Map();

        rows.forEach((row, idx) => {
          const value = row[pkCol.name];

          if (value === '' || value === null || value === undefined) {
            return;
          }

          const normalizedValue = typeof value === 'string' ? value.trim() : value;

          if (!valueMap.has(normalizedValue)) {
            valueMap.set(normalizedValue, []);
          }

          valueMap.get(normalizedValue).push(idx);
        });

        valueMap.forEach((indices, value) => {
          if (indices.length > 1) {
            indices.forEach(idx => {

              if (!allErrors[idx]) {
                allErrors[idx] = {};
              }
              allErrors[idx][pkCol.name] = `Duplicate primary key value "${value}" found in rows ${indices.map(i => i + 1).join(', ')}`;
            });
          }
        });
      });
    }

    setValidationErrors(allErrors);
    return Object.keys(allErrors).length === 0;
  };


  //row management funcs
  const handleAddRow = () => {
    if (!tableMetadata) return;

    const emptyRow = {};

    tableMetadata.columns.forEach(col => {
      emptyRow[col.name] = '';
    });

    setRows([...rows, emptyRow]);
    setHasDraftData(true);
  };


  const handleDeleteRow = (rowIndex) => {
    const newRows = rows.filter((_, idx) => idx !== rowIndex);
    setRows(newRows.length > 0 ? newRows : []);

    const newErrors = {...validationErrors};
    delete newErrors[rowIndex];
    const reindexedErrors = {};

    Object.keys(newErrors).forEach(key => {
      const idx = parseInt(key);

      if (idx > rowIndex) {
        reindexedErrors[idx - 1] = newErrors[key];
      } else {
        reindexedErrors[idx] = newErrors[key];
      }
    });

    setValidationErrors(reindexedErrors);
    setHasDraftData(newRows.length > 0);
  };


  const handleClearAll = () => {
    if (!tableMetadata) return;
    initializeRows(tableMetadata);
    setHasDraftData(false);
  };

  
  const handleCellChange = (rowIndex, columnName, value) => {
    const newRows = [...rows];
    newRows[rowIndex][columnName] = value;
    setRows(newRows);
    setHasDraftData(true);

    if (validationErrors[rowIndex]?.[columnName]) {
      const newErrors = {...validationErrors};
      delete newErrors[rowIndex][columnName];

      if (Object.keys(newErrors[rowIndex]).length === 0) {
        delete newErrors[rowIndex];
      }
      setValidationErrors(newErrors);
    }
  };


  const getInputPlaceholder = (column) => {
    const type = column.type.toLowerCase();

    if (column.nullable) {
      if (type.includes('int')) return 'e.g., 123 (or leave empty for NULL)';
      if (type.includes('varchar') || type.includes('text')) return 'Enter text (or leave empty for NULL)';
      if (type.includes('bool')) return 'true/false (or leave empty for NULL)';
      if (type.includes('date') && !type.includes('timestamp')) return 'YYYY-MM-DD (or leave empty for NULL)';
      if (type.includes('timestamp')) return 'YYYY-MM-DD HH:MM:SS (or leave empty for NULL)';
      if (type.includes('uuid')) return 'UUID format (or leave empty for NULL)';
      if (type.includes('json')) return '{"key": "value"} (or leave empty for NULL)';

      return 'Leave empty for NULL';

    } else {
      if (type.includes('int')) return 'e.g., 123';
      if (type.includes('varchar') || type.includes('text')) return 'Enter text';
      if (type.includes('bool')) return 'true/false';
      if (type.includes('date') && !type.includes('timestamp')) return 'YYYY-MM-DD';
      if (type.includes('timestamp')) return 'YYYY-MM-DD HH:MM:SS';
      if (type.includes('uuid')) return 'UUID format';
      if (type.includes('json')) return '{"key": "value"}';

      return 'Enter value';
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

    setUploadedFile(null);
    setParsedData(null);
    setColumnMapping({});
    setMappingValidation(null);
    setUploadStep('select');
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    onClose();
  };

  const confirmClose = () => {
    resetAndClose();
  };

  const cancelClose = () => {
    setShowCloseConfirmation(false);
  };

  // File upload handlers
  const handleFileSelect = (file) => {
    if (!file) return;

    //validate file type
    const typeValidation = validateFileType(file);
    if (!typeValidation.valid) {
      setError(typeValidation.error);
      return;
    }

    //validate file size
    const sizeValidation = validateFileSize(file);
    if (!sizeValidation.valid) {
      setError(sizeValidation.error);
      return;
    }

    setUploadedFile(file);
    setError('');
    setLoading(true);

    // read and parse 
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      parseFile(file, content);
    };

    reader.onerror = () => {
      setError('Failed to read file');
      setLoading(false);
    };

    reader.readAsText(file);
  };

  const parseFile = (file, content) => {
    const fileName = file.name.toLowerCase();
    let result;

    if (fileName.endsWith('.csv')) {
      result = parseCSV(content);

    } else if (fileName.endsWith('.json')) {
      result = parseJSON(content);

    } else {
      setError('Unsupported file type');
      setLoading(false);
      return;
    }

    setLoading(false);

    if (!result.success) {
      setError(result.error);
      setParsedData(null);
      return;
    }

    //show info msg if truncated
    if (result.message) {
      setToast({ type: 'info', message: result.message });
    }

    setParsedData(result);

    //auto match cols
    if (tableMetadata) {
      const mapping = autoMatchColumns(result.headers, tableMetadata.columns);
      setColumnMapping(mapping);

      const validation = validateColumnMapping(mapping, tableMetadata.columns);
      setMappingValidation(validation);

      setUploadStep('mapping');

    } else {
      setUploadStep('mapping');
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleColumnMappingChange = (uploadedColumn, tableColumn) => {
    const newMapping = {
      ...columnMapping,
      [uploadedColumn]: tableColumn === '' ? null : tableColumn
    };

    setColumnMapping(newMapping);

    const validation = validateColumnMapping(newMapping, tableMetadata.columns);
    setMappingValidation(validation);
  };

  const handleApplyMapping = () => {
    if (!mappingValidation?.valid) {
      setToast({ type: 'error', message: 'Please fix mapping errors before continuing' });
      return;
    }

    const mappedRows = applyColumnMapping(parsedData.rows, columnMapping, tableMetadata.columns);
    setRows(mappedRows);
    setHasDraftData(true);

    setActiveTab('manual');
    setUploadStep('preview');

    setToast({
      type: 'success',
      message: `Successfully imported ${mappedRows.length} rows. Review and insert when ready.`
    });
  };

  const handleResetUpload = () => {
    setUploadedFile(null);
    setParsedData(null);
    setColumnMapping({});
    setMappingValidation(null);
    setUploadStep('select');
    setError('');

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleInsertClick = () => {
    const isValid = validateAllRows();

    if (!isValid) {
      setToast({ type: 'error', message: 'Please fix validation errors before inserting' });
      return;
    }
    setShowInsertConfirmation(true);
  };

  const handleConfirmInsert = async () => {
    setShowInsertConfirmation(false);
    setIsInserting(true);
    setError('');

    try {
      const tableName = selectedTable;

      const validRows = rows.filter(row => {
        return Object.values(row).some(val => val !== '' && val !== null);
      });

      if (validRows.length === 0) {
        setToast({ type: 'error', message: 'No valid rows to insert' });
        setIsInserting(false);
        return;
      }

      const response = await dataAPI.insertData(tableName, validRows);

      if (response.success) {
        const message = response.errors && response.errors.length > 0
          ? `${response.message}. ${response.errors.length} row(s) had errors.`
          : response.message;

        setToast({ type: 'success', message });
        setRows([]);
        setValidationErrors({});
        setHasDraftData(false);

        if (uploadStep === 'preview') {
          handleResetUpload();
        }


        setTimeout(() => {
          resetAndClose();
        }, 2000);

      } else {
        setError(response.message || 'Failed to insert data');
        setToast({ type: 'error', message: response.message || 'Failed to insert data' });
      }

    } catch (err) {
      const errorMessage = err.message || 'Failed to insert data. Please try again.';
      setError(errorMessage);
      setToast({ type: 'error', message: errorMessage });

    } finally {
      setIsInserting(false);
    }
  };

  const handleCancelInsert = () => {
    setShowInsertConfirmation(false);
  };

  if (!isOpen) return null;

  return (
    <>
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


              {/* manual entry */}
              {activeTab === 'manual' && selectedTable && tableMetadata && (
                <div className = "space-y-4">

                  {/* validation summary */}
                  {rows.length > 0 && (
                    <div className = "bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg p-4">

                      <div className = "flex items-center justify-between mb-3">
                        <h4 className = "text-sm font-semibold text-gray-700 dark:text-gray-300">
                          Data Summary
                        </h4>
                      </div>

                      <div className = "grid grid-cols-3 gap-4 text-sm">
                        <div className = "text-center">
                          <div className = "text-2xl font-bold text-blue-600 dark:text-blue-400">
                            {rows.length}
                          </div>

                          <div className = "text-xs text-gray-600 dark:text-gray-400 mt-1">
                            Total Rows
                          </div>
                        </div>

                        <div className = "text-center">
                          <div className = "text-2xl font-bold text-green-600 dark:text-green-400">
                            {rows.length - Object.keys(validationErrors).length}
                          </div>

                          <div className = "text-xs text-gray-600 dark:text-gray-400 mt-1">
                            Valid Rows
                          </div>
                        </div>

                        <div className = "text-center">
                          <div className = "text-2xl font-bold text-red-600 dark:text-red-400">
                            {Object.keys(validationErrors).length}
                          </div>

                          <div className = "text-xs text-gray-600 dark:text-gray-400 mt-1">
                            Rows with Errors
                          </div>
                        </div>
                      </div>

                      {Object.keys(validationErrors).length > 0 && (
                        <div className = "mt-3 pt-3 border-t border-gray-200 dark:border-slate-700">
                          <p className = "text-xs text-red-600 dark:text-red-400 flex items-center space-x-1">
                            <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                              <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>

                            <span>Please fix validation errors before inserting data</span>
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  <div className = "flex items-center justify-between">
                    <div className = "flex items-center space-x-4">
                      <span className = "text-sm font-medium text-gray-700 dark:text-gray-300">
                        {rows.length} row{rows.length !== 1 ? 's' : ''}
                      </span>

                      {Object.keys(validationErrors).length > 0 && (
                        <span className = "text-sm text-red-600 dark:text-red-400 flex items-center space-x-1">
                          <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>

                          <span>{Object.keys(validationErrors).length} row{Object.keys(validationErrors).length !== 1 ? 's have' : ' has'} errors</span>
                        </span>
                      )}
                    </div>

                    <div className = "flex items-center space-x-2">
                      <button
                        onClick = {handleAddRow}
                        className = "px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-1"
                      >
                        <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                          <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 4v16m8-8H4" />
                        </svg>

                        <span>Add Row</span>
                      </button>

                      <button
                        onClick = {handleClearAll}
                        disabled = {rows.length === 0}
                        className = "px-3 py-1.5 text-sm bg-gray-200 hover:bg-gray-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
                      >
                        <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                          <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>

                        <span>Clear All</span>
                      </button>
                    </div>
                  </div>

                  {/* data entry */}
                  <div className = "border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
                    <div className = "overflow-x-auto max-h-96 overflow-y-auto">
                      <table className = "w-full">

                        <thead className = "bg-gray-100 dark:bg-slate-800 sticky top-0">
                          <tr>
                            <th className = "px-2 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 w-10">
                              #
                            </th>

                            {tableMetadata.columns.map((col, idx) => (
                              <th key = {idx} className = "px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">
                                <div className = "flex items-center space-x-1">
                                  <span>{col.name}</span>

                                  {!col.nullable && !col.is_pk && (
                                    <span className = "text-red-500" title = "Required">*</span>
                                  )}

                                  {col.is_pk && (
                                    <span className = "text-purple-500 text-xs" title = "Primary Key">PK</span>
                                  )}
                                </div>

                                <div className = "text-[10px] text-gray-500 dark:text-gray-500 font-normal font-mono mt-0.5">
                                  {col.type}
                                </div>
                              </th>
                            ))}
                            <th className = "px-2 py-2 w-10"></th>
                          </tr>
                        </thead>

                        <tbody className = "divide-y divide-gray-200 dark:divide-slate-700">
                          {rows.map((row, rowIdx) => (
                            <tr key = {rowIdx} className = "hover:bg-gray-50 dark:hover:bg-slate-800/50">
                              <td className = "px-2 py-2 text-xs text-gray-500 dark:text-gray-500 text-center">
                                {rowIdx + 1}
                              </td>

                              {tableMetadata.columns.map((col, colIdx) => (
                                <td key = {colIdx} className = "px-3 py-2">
                                  <div>
                                    <input
                                      type = "text"
                                      value = {row[col.name] || ''}
                                      onChange = {(e) => handleCellChange(rowIdx, col.name, e.target.value)}
                                      placeholder = {getInputPlaceholder(col)}
                                      disabled = {col.is_pk && (col.type.toLowerCase().includes('serial') || col.type.toLowerCase().includes('uuid'))}
                                      className = {`w-full min-w-[150px] px-2 py-1.5 text-sm border rounded transition-colors ${
                                        validationErrors[rowIdx]?.[col.name]
                                          ? 'border-red-300 dark:border-red-600 bg-red-50 dark:bg-red-900/20'
                                          : !col.nullable && !col.is_pk
                                          ? 'border-yellow-300 dark:border-yellow-700 bg-white dark:bg-slate-900'
                                          : 'border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                                      } text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100 dark:disabled:bg-slate-800`}
                                    />
                                    {validationErrors[rowIdx]?.[col.name] && (
                                      <p className = "mt-1 text-xs text-red-600 dark:text-red-400">
                                        {validationErrors[rowIdx][col.name]}
                                      </p>
                                    )}
                                  </div>
                                </td>
                              ))}

                              <td className = "px-2 py-2">
                                <button
                                  onClick = {() => handleDeleteRow(rowIdx)}
                                  className = "p-1 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                  title = "Delete row"
                                >
                                  <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                                  </svg>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>

                      </table>
                    </div>
                  </div>

                  {/* Help text */}
                  <div className = "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3">
                    <p className = "text-xs text-blue-700 dark:text-blue-400">
                      <strong>Tips:</strong> Leave fields empty for NULL values (if nullable). Fields marked with * are required. Primary keys marked as serial or UUID may be auto-generated.
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'upload' && selectedTable && tableMetadata && (
                <div className = "space-y-4">

                  {uploadStep === 'select' && (
                    <>
                      {/* file dropzone */}
                      <div
                        onDragOver = {handleDragOver}
                        onDragLeave = {handleDragLeave}
                        onDrop = {handleDrop}
                        className = {`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                          isDragging
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500'
                        }`}
                      >
                        <div className = "flex flex-col items-center space-y-4">
                          <svg className = "w-12 h-12 text-gray-400 dark:text-gray-500" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>

                          <div>
                            <p className = "text-sm text-gray-700 dark:text-gray-300 mb-1">
                              Drag and drop your file here, or
                            </p>

                            <button
                              onClick = {() => fileInputRef.current?.click()}
                              className = "text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
                            >
                              browse to upload
                            </button>

                            <input
                              ref = {fileInputRef}
                              type = "file"
                              accept = ".csv,.json"
                              onChange = {handleFileInputChange}
                              className = "hidden"
                            />
                          </div>

                          <div className = "text-xs text-gray-500 dark:text-gray-400 space-y-1">
                            <p>Supported formats: CSV, JSON</p>
                            <p>Maximum file size: {MAX_FILE_SIZE / 1024 / 1024}MB</p>
                            <p>Maximum rows: {MAX_ROWS.toLocaleString()}</p>
                          </div>
                        </div>
                      </div>

                      {/* file format info */}
                      <div className = "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                        <h4 className = "text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">
                          File Format Guidelines
                        </h4>

                        <div className = "text-xs text-blue-700 dark:text-blue-400 space-y-2">
                          <div>
                            <strong>CSV:</strong>
                            <ul className = "list-disc list-inside ml-2 mt-1 space-y-0.5">
                              <li>First row should contain column headers</li>
                              <li>Comma, semicolon, tab, or pipe delimiters are auto-detected</li>
                              <li>Use quotes for values containing commas or line breaks</li>
                              <li>Empty cells will be treated as NULL</li>
                            </ul>
                          </div>

                          <div>
                            <strong>JSON:</strong>
                            <ul className = "list-disc list-inside ml-2 mt-1 space-y-0.5">
                              <li>Must be an array of objects</li>
                              <li>Each object represents one row</li>
                              <li>Object keys should match column names</li>
                              <li>Example: {`[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]`}</li>
                            </ul>
                          </div>

                        </div>
                      </div>
                    </>
                  )}

                  {uploadStep === 'mapping' && parsedData && (
                    <>
                      {/* column mapping */}
                      <div className = "space-y-4">
                        <div className = "flex items-center justify-between">
                          <div>
                            <h3 className = "text-sm font-semibold text-gray-700 dark:text-gray-300">
                              Map Columns
                            </h3>

                            <p className = "text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Match uploaded columns to table columns ({parsedData.parsedRows} rows loaded)
                            </p>
                          </div>

                          <button
                            onClick = {handleResetUpload}
                            className = "text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 flex items-center space-x-1"
                          >
                            <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                              <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M6 18L18 6M6 6l12 12" />
                            </svg>

                            <span>Clear</span>
                          </button>
                        </div>

                        {/* mapping table */}
                        <div className = "border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
                          <table className = "w-full">
                            <thead className = "bg-gray-100 dark:bg-slate-800">
                              <tr>
                                <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                                  Uploaded Column
                                </th>

                                <th className = "px-4 py-2 text-center text-xs font-semibold text-gray-600 dark:text-gray-400">
                                  →
                                </th>

                                <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                                  Table Column
                                </th>

                                <th className = "px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                                  Sample Value
                                </th>
                              </tr>
                            </thead>

                            <tbody className = "divide-y divide-gray-200 dark:divide-slate-700">
                              {parsedData.headers.map((uploadedCol, idx) => {
                                const sampleValue = parsedData.rows[0]?.[uploadedCol];
                                const mappedCol = columnMapping[uploadedCol];
                                const isUnmapped = mappedCol === null;

                                return (
                                  <tr key = {idx} className = {`hover:bg-gray-50 dark:hover:bg-slate-800/50 ${isUnmapped ? 'opacity-60' : ''}`}>
                                    <td className = "px-4 py-2 text-sm text-gray-900 dark:text-gray-100 font-medium">
                                      {uploadedCol}
                                    </td>

                                    <td className = "px-4 py-2 text-center">
                                      <svg className = "w-4 h-4 text-gray-400 mx-auto" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M13 7l5 5m0 0l-5 5m5-5H6" />
                                      </svg>
                                    </td>

                                    <td className = "px-4 py-2">
                                      <select
                                        value = {mappedCol || ''}
                                        onChange = {(e) => handleColumnMappingChange(uploadedCol, e.target.value)}
                                        className = "w-full px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                      >
                                        <option value = "">-- Skip this column --</option>

                                        {tableMetadata.columns.map((col) => (
                                          <option key = {col.name} value = {col.name}>
                                            {col.name} ({col.type})
                                          </option>
                                        ))}
                                      </select>
                                    </td>

                                    <td className = "px-4 py-2 text-xs text-gray-500 dark:text-gray-400 font-mono max-w-xs truncate">
                                      {sampleValue !== null && sampleValue !== undefined ? String(sampleValue) : <span className = "italic">null</span>}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>

                        {/* validation msgs */}
                        {mappingValidation && (
                          <div className = "space-y-2">
                            {mappingValidation.errors.length > 0 && (
                              <div className = "px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                <div className = "flex items-start space-x-2">
                                  <svg className = "w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>

                                  <div className = "flex-1">
                                    <p className = "text-sm font-medium text-red-800 dark:text-red-300 mb-1">
                                      Mapping Errors
                                    </p>

                                    <ul className = "text-xs text-red-700 dark:text-red-400 space-y-0.5 list-disc list-inside">
                                      {mappingValidation.errors.map((err, idx) => (
                                        <li key = {idx}>{err}</li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            )}

                            {mappingValidation.warnings.length > 0 && (
                              <div className = "px-4 py-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                                <div className = "flex items-start space-x-2">
                                  <svg className = "w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                    <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                  </svg>

                                  <div className = "flex-1">
                                    <p className = "text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-1">
                                      Warnings
                                    </p>

                                    <ul className = "text-xs text-yellow-700 dark:text-yellow-400 space-y-0.5 list-disc list-inside">
                                      {mappingValidation.warnings.map((warn, idx) => (
                                        <li key = {idx}>{warn}</li>
                                      ))}
                                    </ul>
                                  </div>

                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* apply button */}
                        <div className = "flex justify-end space-x-3">
                          <button
                            onClick = {handleResetUpload}
                            className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors text-sm"
                          >
                            Cancel
                          </button>

                          <button
                            onClick = {handleApplyMapping}
                            disabled = {!mappingValidation?.valid}
                            className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center space-x-2"
                          >
                            <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                              <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                            </svg>

                            <span>Apply & Preview ({parsedData.parsedRows} rows)</span>
                          </button>
                        </div>
                      </div>
                    </>
                  )}
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


          {/* bottom buttons */}
          <div className = "px-6 py-4 border-t border-gray-200 dark:border-slate-700 flex justify-end space-x-3">
            <button
              onClick = {handleClose}
              className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
            >
              Cancel
            </button>


            {activeTab === 'manual' && selectedTable && rows.length > 0 ? (
              <button
                onClick = {handleInsertClick}
                disabled = {rows.length === 0 || Object.keys(validationErrors).length > 0 || isInserting}
                className = "px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isInserting ? (
                  <>
                    <svg className = "animate-spin h-4 w-4" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
                      <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
                      <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>

                    <span>Inserting...</span>
                  </>
                ) : (
                  <>
                    <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                      <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                    </svg>

                    <span>Insert {rows.length} Row{rows.length !== 1 ? 's' : ''}</span>
                  </>
                )}
              </button>

            ) : (
              <button
                disabled = {!selectedTable}
                className = "px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            )}


          </div>

        </div>
      </div>

      {/* close confirmation */}
      {showCloseConfirmation && (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className = "text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
              Discard Changes?
            </h3>

            <p className = "text-sm text-gray-600 dark:text-gray-400 mb-6">
              You have unsaved data. Are you sure you want to close this modal? All changes will be lost.
            </p>

            <div className = "flex justify-end space-x-3">
              <button
                onClick = {cancelClose}
                className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
              >
                Keep Editing
              </button>

              <button
                onClick = {confirmClose}
                className = "px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Discard Changes
              </button>
            </div>

          </div>
        </div>
      )}

      {/* insert confirmation */}
      {showInsertConfirmation && (
        <div className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className = "bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <div className = "flex items-start space-x-3 mb-4">

              <div className = "flex-shrink-0 w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <svg className = "w-6 h-6 text-green-600 dark:text-green-400" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                </svg>
              </div>

              <div className = "flex-1">
                <h3 className = "text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                  Confirm Data Insert
                </h3>

                <div className = "text-sm text-gray-600 dark:text-gray-400 space-y-2">
                  <p>
                    You are about to insert <strong className = "text-gray-800 dark:text-gray-100">{rows.length} row{rows.length !== 1 ? 's' : ''}</strong> into:
                  </p>

                  <p className = "font-mono text-xs bg-gray-100 dark:bg-slate-900 px-2 py-1 rounded">
                    {selectedTable}
                  </p>

                  {(() => {
                    const nullableAutoFills = tableMetadata?.columns.filter(col => {
                      const hasData = rows.some(row => row[col.name] !== null && row[col.name] !== '');
                      return col.nullable && !hasData;
                    }) || [];

                    if (nullableAutoFills.length > 0) {
                      return (
                        <p className = "text-xs">
                          <strong>Note:</strong> {nullableAutoFills.length} nullable column{nullableAutoFills.length !== 1 ? 's' : ''} will be set to NULL.
                        </p>
                      );
                    }

                    return null;
                  })()}

                  <p className = "text-xs text-yellow-700 dark:text-yellow-400 mt-3">
                    This action cannot be undone.
                  </p>
                </div>
              </div>
            </div>

            <div className = "flex justify-end space-x-3 mt-6">
              <button
                onClick = {handleCancelInsert}
                className = "px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
              >
                Cancel
              </button>

              <button
                onClick = {handleConfirmInsert}
                className = "px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                  <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                </svg>

                <span>Confirm Insert</span>
              </button>
            </div>

          </div>
        </div>
      )}

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

export default AddDataModal;