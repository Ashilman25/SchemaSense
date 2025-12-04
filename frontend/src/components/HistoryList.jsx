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








});

export default HistoryList;