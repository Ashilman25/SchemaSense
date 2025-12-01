import {useState, useEffect} from 'react';
import {schemaAPI} from '../../utils/api';

const TableDetailPanel = ({table, schema, onClose, onAskAboutTable}) => {
    const [sampleRows, setSampleRows] = useState(null);
    const [loadingSampleRows, setLoadingSampleRows] = useState(false);
    const [sampleRowsError, setSampleRowsError] = useState(null);

    const tableKey = `${table.schema}.${table.name}`;

    useEffect(() => {
        setSampleRows(null);
        setSampleRowsError(null);
    }, [tableKey]);

    //relations
    const outgoingFKs = schema.relationships?.filter(rel => rel.from_table === tableKey) || [];
    const incomingFKs = schema.relationships?.filter(rel => rel.to_table === tableKey) || [];

    const handlePreviewSampleRows = async () => {
        setLoadingSampleRows(true);
        setSampleRowsError(null);

        try {
            const data = await schemaAPI.getSampleRows(tableKey, 10);
            setSampleRows(data);

        } catch (err) {
            setSampleRowsError(err.message || 'Failed to load sample rows');

        } finally {
            setLoadingSampleRows(false);
        }
    };

    const handleAskAboutTable = () => {
        onAskAboutTable(tableKey);
        //onClose();
    }







};

export default TableDetailPanel;