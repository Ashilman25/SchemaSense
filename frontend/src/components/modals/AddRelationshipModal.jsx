import {useState, useEffect} from 'react';

const AddRelationshipModal = ({isOpen, onClose, onSubmit, schema, currentTable}) => {
    const [fromColumn, setFromColumn] = useState('');
    const [toTable, setToTable] = useState('');
    const [toColumn, setToColumn] = useState('');
    const [error, setError] = useState(null);

    const availableColumns = currentTable?.columns || [];
    const availableTables = schema?.tables?.filter(t => `${t.schema}.${t.name}` !== `${currentTable?.schema}.${currentTable?.name}`) || [];

    
    const selectedTable = availableTables.find(t => `${t.schema}.${t.name}` === toTable);
    const availableTargetColumns = selectedTable?.columns || [];

    useEffect(() => {
        if (isOpen) {
            setFromColumn('');
            setToTable('');
            setToColumn('');
            setError(null);
        }

    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!fromColumn) {
            setError("Please select a column from the current table");
            return;
        }

        if (!toTable) {
            setError("Please select a target table");
            return;
        }

        if (!toColumn) {
            setError("Please select a target column");
            return;
        }

        try {
            await onSubmit({
                from_table: `${currentTable.schema}.${currentTable.name}`,
                from_column: fromColumn,
                to_table: toTable,
                to_column: toColumn
            });

            handleClose();

        } catch (err) {
            setError(err.message || 'Failed to add relationship');
        }
    };

    const handleClose = () => {
        setFromColumn('');
        setToTable('');
        setToColumn('');
        setError(null);
        onClose();
    };

    if (!isOpen) return null;


};

export default AddRelationshipModal;