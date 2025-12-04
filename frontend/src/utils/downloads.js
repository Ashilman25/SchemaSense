export function convertToJSON(columns, rows) {
    if (!columns || rows) {
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