export function convertToJSON(columns, rows) {
    if (!columns || !rows) {
        return [];
    }

    return rows.map(row => {
        const obj = {};

        columns.forEach((column, index) => {
            obj[column] = row[index] === null ? null : row[index];
        });

        return obj;
    });
}


export function serializeJSON(data) {
    return JSON.stringify(data, null, 2);
}



//formating
function escapeCSVField(value) {
    if (value === null || value === undefined) {
        return '';
    }

    let stringValue = String(value);
    const needsQuoting = /[",\n\r]/.test(stringValue); //check if contains comma, quote, or newline

    if (needsQuoting) {
        stringValue = '"' + stringValue.replace(/"/g, '""') + '"';
    }

    return stringValue;
}

//cols and rows to csv
export function convertToCSV(columns, rows) {
    if (!columns || !rows) {
        return '';
    }

    const header = columns.map(col => escapeCSVField(col)).join(',');

    const dataRows = rows.map(row => {
        return row.map(cell => escapeCSVField(cell)).join(',');
    });

    return [header, ...dataRows].join('\n');
}


function sanitizeFilename(name) {
    if (!name) {
        return 'results';
    }

    return name.trim().replace(/[^a-zA-Z0-9_\s-]/g, '').replace(/\s+/g, '_').toLowerCase().substring(0, 50);

}

function generateTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}



export function generateFilename(baseName, extension) {
    const sanitized = sanitizeFilename(baseName);
    const timestamp = generateTimestamp();

    return `${sanitized}_${timestamp}.${extension}`;
}


export function triggerDownload(content, filename, mimeType) {
    const blob = new Blob([content], {type: mimeType});
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
        URL.revokeObjectURL(url);
    }, 100);
}


export function exportAsJson(columns, rows, baseName = 'results') {
    const data = convertToJSON(columns, rows);
    const jsonContent = serializeJSON(data);
    const filename = generateFilename(baseName, 'json');

    triggerDownload(jsonContent, filename, 'application/json');
}

export function exportAsCSV(columns, rows, baseName = 'results') {
    const csvContent = convertToCSV(columns, rows);
    const filename = generateFilename(baseName, 'csv');

    triggerDownload(csvContent, filename, 'text/csv;charset=utf-8;');
}