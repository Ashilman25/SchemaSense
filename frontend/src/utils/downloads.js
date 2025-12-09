import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

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




function convertToTextTable(columns, rows) {
    if (!columns || !rows) {
        return '';
    }

    const headers = columns.map(col => (col == null ? '' : String(col)));

    const dataRows = rows.map(row => 
        row.map(cell => {
            if (cell === null || cell === undefined) {
                return 'NULL';
            }
            return String(cell);
        })
    );

    const colCount = headers.length;
    const colWidths = new Array(colCount).fill(0);

    headers.forEach((h, i) => {
        colWidths[i] = Math.max(colWidths[i], h.length);
    });

    const padCell = (text, width) => text = ' '.repeat(Math.max(0, width - text.length));

    const headerLine = headers.map((h, i) => padCell(h, colWidths[i])).join(' | ');
    const separatorLine = colWidths.map(w => '-'.repeat(w)).join('-+-');

    const bodyLines = dataRows.map(row => row.map((cell, i) => padCell(cell, colWidths[i])).join(' | '));

    return [headerLine, separatorLine, ...bodyLines].join('\n');

}




export async function exportAsPDF(columns, rows, baseName = 'results', queryTitle = null) {
    try {
        if (!columns || !rows || rows.length === 0) {
            console.warn('No data to export');
            return;
        }

        const doc = new jsPDF({
            orientation: 'landscape',
            unit: 'mm',
            format: 'a4'
        });

        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 14;

        //title header
        const titleText = 'Query Results Report';
        const timestamp = new Date().toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        //title style
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(31, 41, 55);
        doc.text(titleText, margin, margin + 8);

        //subtitle and timestamp
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(107, 114, 128);
        doc.text(`Generated: ${timestamp}`, margin, margin + 15);
        doc.text(`Total Rows: ${rows.length}`, margin, margin + 20);

        const tableData = rows.map(row => 
            row.map(cell => {
                if (cell === null || cell === undefined) {
                    return 'NULL';
                }

                //truncate if necessary
                const cellStr = String(cell);
                return cellStr.length > 500 ? cellStr.substring(0, 497) + '...' : cellStr;
            })
        );


        autoTable(doc, {
            head: [columns],
            body: tableData,
            startY: margin + 25,
            margin: {left: margin, right: margin},
            theme: 'striped',
            headStyles: {
                fillColor: [59, 130, 246], //might change this blue
                textColor: [255, 255, 255],
                fontStyle: 'bold',
                fontSize: 10,
                halign: 'left',
                cellPadding: 4
            },

            bodyStyles: {
                fontSize: 9,
                cellPadding: 3,
                textColor: [31, 41, 55],
                lineColor: [229, 231, 235],
                lineWidth: 0.1
            },

            alternateRowStyles: {
                fillColor: [249, 250, 251]
            },

            styles: {
                overflow: 'linebreak',
                cellWidth: 'wrap',
                minCellHeight: 8,
                halign: 'left',
                valign: 'middle'
            },

            showHead: 'everyPage',

            //page breaks
            didDrawPage: () => {
                doc.setFontSize(8);
                doc.setFont('helvetica', 'normal');
                doc.setTextColor(156, 163, 175);

                const pageNumText = `Page ${doc.internal.getCurrentPageInfo().pageNumber}`;
                const footerText = 'SchemaSense Query Results';

                doc.text(footerText, margin, pageHeight - 10);
                doc.text(
                    pageNumText,
                    pageWidth - margin - doc.getTextWidth(pageNumText),
                    pageHeight - 10
                );            
            }
        });

        //filename and save
        const filename = generateFilename(baseName, 'pdf');
        doc.save(filename);

        return true;

    } catch (error) {
        console.error('PDF export failed: ', error);
        throw new Error(`Failed to generate PDF: ${error.message}`);
    }
}