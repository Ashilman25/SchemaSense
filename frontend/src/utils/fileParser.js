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

