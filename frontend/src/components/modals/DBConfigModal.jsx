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




        
      </div>
    </div>
  );
};

export default DBConfigModal;
