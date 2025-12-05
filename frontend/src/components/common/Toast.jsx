import { useEffect } from "react";

const Toast = ({message, type = 'success', duration = 3000, onClose}) => {

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const typeStyles = {
    success: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-700 dark:text-green-400',
      icon: (
        <svg className = "w-5 h-5" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule = "evenodd" />
        </svg>
      ),
    },
    
    error: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-700 dark:text-red-400',
      icon: (
        <svg className = "w-5 h-5" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule = "evenodd" />
        </svg>
      ),
    },
    
    info: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-700 dark:text-blue-400',
      icon: (
        <svg className = "w-5 h-5" fill = "currentColor" viewBox = "0 0 20 20">
          <path fillRule = "evenodd" d = "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule = "evenodd" />
        </svg>
      ),
    },
  };

  const styles = typeStyles[type] || typeStyles.info;

  return (
    <div className = "fixed top-4 right-4 z-50 animate-fade-in">
      <div className = {`flex items-start space-x-3 px-4 py-3 border rounded-lg shadow-lg ${styles.bg} ${styles.border} ${styles.text} max-w-md`}>
        <div className = "flex-shrink-0 mt-0.5">
          {styles.icon}
        </div>

        <div className = "flex-1">
          <p className = "text-sm font-medium">{message}</p>
        </div>

        <button
          onClick = {onClose}
          className = "flex-shrink-0 ml-3 hover:opacity-70 transition-opacity"
        >
          <svg className = "w-4 h-4" fill = "currentColor" viewBox = "0 0 20 20">
            <path fillRule = "evenodd" d = "M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule = "evenodd" />
          </svg>
        </button>

      </div>
    </div>
  );


};

export default Toast;