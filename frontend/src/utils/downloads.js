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