import {useState, useEffect, forwardRef, useImperativeHandle} from 'react';
import { historyAPI } from '../utils/api';

//time format
const formatRelativeTime = (timestamp) => {
  const now = new Date();
  const past = new Date(timestamp);
  const diffInSeconds = Math.floor((now - past) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

  //if older, just show date
  return past.toLocaleDateString();
}


const HistoryList = forwardRef(({onHistoryItemClick, isDbConnected}, ref) => {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchHistory = async () => {
    if (!isDbConnected) {
      setHistory([]);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const data = await historyAPI.getHistory(50); //maybe less later, 50 a lot, maybe 10?
      setHistory(data);

    } catch (err) {
      console.error("Failed to fetch history: ", err);
      setError("Failed to load history");
      setHistory([]);

    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [isDbConnected]);

  useImperativeHandle(ref, () => ({
    refresh: fetchHistory
  }));

  const handleItemClick = (item) => {
    if (onHistoryItemClick) {
      onHistoryItemClick(item);
    }
  };


  //icons
  const StatusIcon = ({status}) => {
    if (status === 'success') {
      return (
        <svg className = "w-4 h-4 text-green-500 dark:text-green-400 flex-shrink-0" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule = "evenodd" />
        </svg>
      );

    } else if (status === 'error') {
      return (
        <svg className = "w-4 h-4 text-red-500 dark:text-red-400 flex-shrink-0" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule = "evenodd" />
        </svg>
      );

    } else {
      return (
        <svg className = "w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule = "evenodd" />
        </svg>
      );
    }
  };


  if (!isDbConnected) {
    return (
      <div className = "flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
        <p>Connect to database to view history</p>
      </div>
    );
  }

  if (isLoading && history.length === 0) {
    return (
      <div className = "flex-1 flex items-center justify-center">
        <svg className = "animate-spin h-5 w-5 text-blue-600 dark:text-blue-400" xmlns = "http://www.w3.org/2000/svg" fill = "none" viewBox = "0 0 24 24">
          <circle className = "opacity-25" cx = "12" cy = "12" r = "10" stroke = "currentColor" strokeWidth = "4"></circle>
          <path className = "opacity-75" fill = "currentColor" d = "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    );
  }


  if (error) {
    return (
      <div className = "flex-1 flex items-center justify-center">
        <div className = "text-center">
          <p className = "text-sm text-red-600 dark:text-red-400">{error}</p>

          <button
            onClick = {fetchHistory}
            className = "mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Retry
          </button>
        </div>
      </div>

    );
  }

  if (history.length === 0) {
    return (
      <div className = "flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
        <p>No query history yet</p>
      </div>
    );
  }














});

export default HistoryList;