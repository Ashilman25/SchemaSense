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

  //on success returns: {success:, message:}
  //on fail returns: {success:, message:, error }
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

  //returns: {connected:}
  getStatus: async () => {
    return apiRequest('/api/config/db', {
      method: 'GET',
    });
  },
};


export const schemaAPI = {

  //returns: {tables: [schema, name, columns], relationships: []}
  getSchema: async () => {
    return apiRequest('/api/schema', {
      method: 'GET',
    });
  },

  //returns: {table:, columns, rows:, row_count}
  getSampleRows: async(table, limit = 10) => {
    const params = new URLSearchParams({
      table,
      limit: String(limit),
    });

    return apiRequest(`/api/schema/sample-rows?${params.toString()}`, {
      method: 'GET',
    });
  },

  //returns: {ddl:, table_count:, relationship_count:}
  getDDL: async () => {
    return apiRequest('/api/schema/ddl', {
      method: 'GET',
    });
  },

  //returns: {success:, schema:, ddl:, errors:}
  applyEREdits: async (actions) => {
    return apiRequest('/api/schema/er-edit', {
      method: 'POST',
      body: JSON.stringify({ actions }),
    });
  },

  //returns: {success:, schema:, ddl:, error:, details:}
  applyDDLEdit: async (ddl) => {
    return apiRequest('/api/schema/ddl-edit', {
      method: 'POST',
      body: JSON.stringify({ ddl }),
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


export const historyAPI = {

  // Returns: array of {id, timestamp, question, sql, status, execution_duration_ms}
  getHistory: async (limit = 50) => {
    const params = new URLSearchParams({
      limit: String(limit),
    });

    return apiRequest(`/api/history?${params.toString()}`, {
      method: 'GET',
    });
  },


  // Returns: {saved: boolean, id: number}
  saveHistory: async (historyItem) => {
    return apiRequest('/api/history', {
      method: 'POST',
      body: JSON.stringify({
        question: historyItem.question,
        sql: historyItem.sql || null,
        status: historyItem.status,
        execution_duration_ms: historyItem.execution_duration_ms || null,
      }),
    });
  },


  // Returns: {success: boolean, id: number, message: string}
  deleteHistory: async (historyId) => {
    return apiRequest(`/api/history/${historyId}`, {
      method: 'DELETE',
    });
  },

};

export default {
  dbConfigAPI,
  schemaAPI,
  nlToSqlAPI,
  sqlAPI,
  historyAPI,
};
