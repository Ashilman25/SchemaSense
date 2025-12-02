import {useState, useEffect} from 'react';

const EditColumnModal = ({isOpen, onClose, onSubmit, column, mode = 'add'}) => {
    const [columnName, setColumnName] = useState('');
    const [columnType, setColumnType] = useState('text');
    const [isPrimaryKey, setIsPrimaryKey] = useState(false);
    const [isForeignKey, setIsForeignKey] = useState(false);
    const [nullable, setNullable] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && column && mode === 'edit') {
            setColumnName(column.name || '');
            setColumnType(column.type || 'text');
            setIsPrimaryKey(column.is_pk || false);
            setIsForeignKey(column.is_fk || false);
            setNullable(column.nullable !== undefined ? column.nullable : true);

        } else if (isOpen && mode === 'add') {
            setColumnName('');
            setColumnType('text');
            setIsPrimaryKey(false);
            setIsForeignKey(false);
            setNullable(true);
        }

        setError(null);

    }, [isOpen, column, mode]);


    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!columnName.trim()) {
            setError("Column name is required");
            return;
        }

        if (!columnType.trim()) {
            setError("Column type is required");
            return;
        }

        try {
            await onSubmit({
                name: columnName.trim(),
                type: columnType.trim(),
                is_pk: isPrimaryKey,
                is_fk: isForeignKey,
                nullable, nullable
            });

            handleClose()

        } catch (err) {
            setError(err.message || `Failed to ${mode} column`);
        }
    };

    const handleClose = () => {
        setColumnName('');
        setColumnType('text');
        setIsPrimaryKey(false);
        setIsForeignKey(false);
        setNullable(true);
        setError(null);
        onClose();
    };

    if (!isOpen) return null;






};

export default EditColumnModal;