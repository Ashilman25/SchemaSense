import {useState} from 'react';

const AddTableModal = ({isOpen, onClose, onSubmit}) => {
    const [tableName, setTableName] = useState('');
    const [schema, setSchema] = useState('public');
    const [columns, setColumns] = useState([{
        name: 'id',
        type: 'serial',
        is_pk: true,
        nullable: false
    }]);
    const [error, setError] = useState(null);

    const handleAddColumn = () => {
        setColumns([...columns, {name: '', type: 'text', is_pk: false, nullable: true}]);
    };

    const handleRemoveColumn = (index) => {
        if (columns.length > 1) {
            setColumns(columns.filter((_, i) => i !== index));
        }
    };

    const handleColumnChange = (index, field, value) => {
        const newColumns = [...columns];
        newColumns[index] = {...newColumns[index], [field]: value};
        setColumns(newColumns);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!tableName.trim()) {
            setError('Table name is required');
            return;
        }

        if (columns.length === 0) {
            setError('At least one column is required');
            return;
        }

        for (let i = 0; i < columns.length; i++) {
            if (!columns[i].name.trim()) {
                setError(`Column ${i + 1} name is required`);
                return;
            }

            if (!columns[i].type.trim()) {
                setError(`Column ${i + 1} type is required`);
                return;
            }
        }


        try {
            await onSubmit({
                tableName: tableName.trim(),
                schema: schema.trim(),
                columns
            });
            handleClose();

        } catch (err) {
            setError(err.message || 'Failed to add table');
        }
    };

    const handleClose = () => {
        setTableName('');
        setSchema('public');
        setColumns([{name: 'id', type: 'serial', is_pk: true, nullable: false}]);
        setError(null);
        onClose();
    };

    if (!isOpen) return null;




};

export default AddTableModal;