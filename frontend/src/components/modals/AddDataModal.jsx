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




};

export default AddDataModal;