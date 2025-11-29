const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';


export const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || `API Error: ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
};


export const dbConfigAPI = {

  testAndSave: async (config) => {
    return apiRequest('/api/config/db', {
      method: 'POST',
      body: JSON.stringify({
        host: config.host,
        port: parseInt(config.port),
        dbname: config.dbname,
        user: config.user,
        password: config.password,
      }),
    });
  },


  getStatus: async () => {
    return apiRequest('/api/config/db', {
      method: 'GET',
    });
  },
};


export const schemaAPI = {

  getSchema: async () => {
    return apiRequest('/api/schema', {
      method: 'GET',
    });
  },
};


export const nlToSqlAPI = {

  generateSQL: async (question) => {
    return apiRequest('/api/nl-to-sql', {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
  },
};


export const sqlAPI = {

  validate: async (sql) => {
    return apiRequest('/api/sql/validate', {
      method: 'POST',
      body: JSON.stringify({ sql }),
    });
  },


  execute: async (sql) => {
    return apiRequest('/api/sql/execute', {
      method: 'POST',
      body: JSON.stringify({ sql }),
    });
  },


  getPlan: async (sql) => {
    return apiRequest('/api/sql/plan', {
      method: 'POST',
      body: JSON.stringify({ sql }),
    });
  },
};

export default {
  dbConfigAPI,
  schemaAPI,
  nlToSqlAPI,
  sqlAPI,
};
