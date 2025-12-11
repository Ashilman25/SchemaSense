export const MAX_FILE_SIZE = 5 * 1024 * 1024; //5MB
export const MAX_ROWS = 1000;

//detect csv separator
const detectDelimiter = (csvText) => {
  const sample = csvText.split('\n').slice(0, 5).join('\n');
  const delimiters = [',', ';', '\t', '|'];

  const counts = delimiters.map(delimiter => ({
    delimiter,
    count: (sample.match(new RegExp(`\\${delimiter}`, 'g')) || []).length
  }));

  counts.sort((a, b) => b.count - a.count);
  return counts[0].count > 0 ? counts[0].delimiter : ',';
};

//parses quotes
const parseCSVLine = (line, delimiter) => {
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"'){
      if (inQuotes && nextChar === '"'){
        current += '"';
        i++;

      } else {
        inQuotes = !inQuotes;
      }

    } else if (char === delimiter && !inQuotes) {
      result.push(current.trim());
      current = '';

    } else {
      current += char;
    }
  }

  result.push(current.trim());
  return result;
};




export const parseCSV = (content) => {
  try {
    const lines = content.split('\n').filter(line => line.trim());

    if (lines.length === 0) {
      throw new Error('CSV file is empty');
    }

    const delimiter = detectDelimiter(content);
    const headers = parseCSVLine(lines[0], delimiter);

    if (headers.length === 0) {
      throw new Error('No columns detected in CSV');
    }

    const rows = [];
    const maxRows = Math.min(lines.length - 1, MAX_ROWS);

    for (let i = 1; i <= maxRows; i++) {
      if (lines[i] && lines[i].trim()) {
        const values = parseCSVLine(lines[i], delimiter);

        const row = {};
        headers.forEach((header, idx) => {
          const value = values[idx] || '';
          row[header] = value === '' ? null : value;
        });

        rows.push(row);
      }
    }

    const totalRows = lines.length - 1;
    const truncated = totalRows > MAX_ROWS;

    return {
      success: true,
      headers,
      rows,
      delimiter,
      totalRows,
      parsedRows: rows.length,
      truncated,
      message: truncated ? `File contains ${totalRows} rows, showing first ${MAX_ROWS}` : null
    };


  } catch (error) {
    return {
      success: false,
      error: error.message || 'Failed to parse CSV file'
    };
  }
};



export const parseJSON = (content) => {
  try {
    const data = JSON.parse(content);

    if (!Array.isArray(data)) {
      throw new Error('JSON must be an array of objects');
    }

    if (data.length === 0) {
      throw new Error('JSON array is empty');
    }

    const invalidItems = data.filter(item => typeof item !== 'object' || item === null || Array.isArray(item));
    if (invalidItems.length > 0) {
      throw new Error('All items in the JSON array must be objects');
    }

    const allKeys = new Set();
    data.forEach(item => {
      Object.keys(item).forEach(key => allKeys.add(key));
    });

    const headers = Array.from(allKeys);
    if (headers.length === 0) {
      throw new Error('No keys found in JSON objects');
    }

    const maxRows = Math.min(data.length, MAX_ROWS);
    const rows = data.slice(0, maxRows).map(item => {
      const row = {};

      headers.forEach(key => {
        const value = item[key];
        row[key] = (value === undefined || value === '' || value === null) ? null : value;
      });

      return row;
    });

    const totalRows = data.length;
    const truncated = totalRows > MAX_ROWS;

    return {
      success: true,
      headers,
      rows,
      totalRows,
      parsedRows: rows.length,
      truncated,
      message: truncated ? `File contains ${totalRows} rows, showing first ${MAX_ROWS}` : null
    };


  } catch (error) {
    return {
      success: false,
      error: error.message || 'Failed to parse JSON file'
    };
  }
};



//VALIDATORS
export const validateFileSize = (file) => {
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds maximum allowed size (${MAX_FILE_SIZE / 1024 / 1024}MB)`
    };
  }

  return {valid: true};
}


export const validateFileType = (file) => {
  const validExtensions = ['.csv', '.json'];
  const fileName = file.name.toLowerCase();
  const isValid = validExtensions.some(ext => fileName.endsWith(ext));

  if (!isValid) {
    return {
      valid: false,
      error: 'Only .csv and .json files are supported'
    };
  }

  return {valid: true};
};



//COLUMN FUNCTIONALITIES

export const autoMatchColumns = (uploadedHeaders, tableColumns) => {
  const mapping = {};
  const tableColumnsNames = tableColumns.map(col => col.name);

  uploadedHeaders.forEach(uploadedHeader => {
    const exactMatch = tableColumnsNames.find(
      col => col.toLowerCase() === uploadedHeader.toLowerCase()
    );

    if (exactMatch) {
      mapping[uploadedHeader] = exactMatch;

    } else {
      const partialMatch = tableColumnsNames.find(
        col => col.toLowerCase().includes(uploadedHeader.toLowerCase()) || uploadedHeader.toLowerCase().includes(col.toLowerCase())
      );

      mapping[uploadedHeader] = partialMatch || null;
    }
  });

  return mapping;

};


export const validateColumnMapping = (mapping, tableColumns) => {
  const mappedTableColumns = new Set(Object.values(mapping).filter(v => v !== null));
  const requiredColumns = tableColumns.filter(col => !col.nullable && !col.is_pk);
  const pkColumns = tableColumns.filter(col => col.is_pk && !col.type.toLowerCase().includes('serial'));
  
  const errors = [];
  const warnings = [];

  requiredColumns.forEach(col => {
    if (!mappedTableColumns.has(col.name)) {
      errors.push(`Required column "${col.name}" is not mapped`);
    }
  });

  //check missing pks
  pkColumns.forEach(col => {
    if (!mappedTableColumns.has(col.name)) {
      errors.push(`Primary key column "${col.name}" is not mapped and must be provided`);
    }
  });


  //check unmapped uploaded cols
  const unmappedUploaded = Object.entries(mapping).filter(([_, tableCol]) => tableCol === null);
  if (unmappedUploaded.length > 0) {
    warnings.push(`${unmappedUploaded.length} uploaded column(s) will be ignored: ${unmappedUploaded.map(([col]) => col).join(', ')}`);
  }


  //check table cols
  const nullableColumns = tableColumns.filter(col => col.nullable && !mappedTableColumns.has(col.name));
  if (nullableColumns.length > 0) {
    warnings.push(`${nullableColumns.length} nullable column(s) not in upload will be set to NULL: ${nullableColumns.map(col => col.name).join(', ')}`);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
};


export const applyColumnMapping = (rows, mapping, tableColumns) => {
  return rows.map(row => {
    const mappedRow = {};

    tableColumns.forEach(col => {
      mappedRow[col.name] = null;
    });

    Object.entries(mapping).forEach(([uploadedCol, tableCol]) => {
      if (tableCol !== null && row[uploadedCol] !== undefined) {
        mappedRow[tableCol] = row[uploadedCol];
      }
    });

    return mappedRow;
  });
};