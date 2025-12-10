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