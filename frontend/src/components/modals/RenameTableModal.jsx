import {useState, useEffect} from 'react';

const RenameTableModal = ({isOpen, onClose, onSubmit, currentName}) => {
    const [newName, setNewName] = useState('');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen) {
            setNewName(currentName || '');
            setError(null);
        }
    }, [isOpen, currentName]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!newName.trim()) {
            setError('Table name is required');
            return;
        }

        if (newName.trim() === currentName) {
            setError("New name must be different from current name");
            return;
        }

        try {
            await onSubmit(newName.trim());
            handleClose();

        } catch (err) {
            setError(err.message || "Failed to rename table");
        }
    };

    const handleClose = () => {
        setNewName('');
        setError(null);
        onClose();
    };

    if (isOpen) return null;




};

export default RenameTableModal;