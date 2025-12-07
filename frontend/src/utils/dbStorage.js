//auto reconnect on reload

const DB_CREDENTIALS_KEY = 'schemasense_db_credentials'

export const saveDBCredentials = (credentials) => {
  try {
    sessionStorage.setItem(DB_CREDENTIALS_KEY, JSON.stringify(credentials));

  } catch (error) {
    console.error('Failed to save DB credentials to sessionStorage: ', error);
    
  }
};


export const loadDBCredentials = () => {
  try {
    const stored = sessionStorage.getItem(DB_CREDENTIALS_KEY);

    if (!stored) {
      return null;
    }

    return JSON.parse(stored);

  } catch (error) {
    console.error('Failed to load DB credentials from sessionStorage: ', error);
    return null;

  }
};


export const clearDBCredentials = () => {
  try {
    sessionStorage.removeItem(DB_CREDENTIALS_KEY);

  } catch (error) {
    console.error('Failed to clear DB credentials from sessionStorage: ', error);
  }
};

export const credentialsMatchDB = (dbname) => {
  const stored = loadDBCredentials();
  return stored && stored.dbname === dbname;
}


