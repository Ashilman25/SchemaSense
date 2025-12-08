import {useEffect, useMemo, useRef, useState} from 'react';

const DATA_TYPE_OPTIONS = [
    'serial',
    'bigserial',
    'smallserial',
    'integer',
    'bigint',
    'smallint',
    'numeric',
    'decimal',
    'real',
    'double precision',
    'money',
    'varchar',
    'char',
    'text',
    'boolean',
    'uuid',
    'date',
    'time',
    'timetz',
    'timestamp',
    'timestamptz',
    'interval',
    'json',
    'jsonb',
    'bytea',
    'inet',
    'cidr',
    'macaddr',
    'xml',
    'tsvector',
    'tsquery',
    'citext',
    'point',
    'line',
    'lseg',
    'box',
    'path',
    'polygon',
    'circle',
    'bit',
    'varbit',
    'enum',
    'array'
];

const COMMON_TYPES = new Set([
    'serial',
    'bigserial',
    'integer',
    'bigint',
    'smallint',
    'numeric',
    'decimal',
    'varchar',
    'text',
    'boolean',
    'uuid',
    'date',
    'timestamp',
    'timestamptz',
    'json',
    'jsonb'
]);



const DataTypeSelect = ({value, onChange, placeholder = "Choose a data type"}) => {
    const [inputValue, setInputValue] = useState(value || '');
    const [isOpen, setIsOpen] = useState(false);
    const [highlightIndex, setHighlightIndex] = useState(0);
    const containerRef = useRef(null);

    useEffect(() => {
        setInputValue(value || '');
    }, [value]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const filteredOptions = useMemo(() => {
        const search = inputValue.trim().toLowerCase();

        const scored = DATA_TYPE_OPTIONS.map((option, index) => {
            const lower = option.toLowerCase();
            const position = lower.indexOf(search);
            const starts = position === 0;

            return {
                option,
                lower,
                position,
                starts,
                distance: Math.abs(lower.length - search.length),
                originalIndex: index
            };
        });

        const filtered = search ? scored.filter(item => item.position !== -1) : scored;

        if (search) {
            filtered.sort((a, b) => {
                if (a.starts !== b.starts) return a.starts ? -1 : 1;
                if (a.position !== b.position) return a.position - b.position;
                if (a.distance !== b.distance) return a.distance - b.distance;

                return a.originalIndex - b.originalIndex;
            });

        } else {
            filtered.sort((a, b) => a.originalIndex - b.originalIndex);
        }

        return filtered.map(item => item.option);
    }, [inputValue]);

    useEffect(() => {
        setHighlightIndex(0);
    }, [filteredOptions.length, isOpen]);

    const handleSelect = (option) => {
        setInputValue(option);
        onChange?.(option);
        setIsOpen(false);
    };

    const handleInputChange = (e) => {
        const nextValue = e.target.value;
        setInputValue(nextValue);
        onChange?.(nextValue);
        setIsOpen(true);
    };

    const handleKeyDown = (e) => {
        if (!isOpen && (e.key === 'ArrowDown' || e.key === 'Enter')) {
            setIsOpen(true);
            return;
        }

        if (!filteredOptions.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setHighlightIndex((prev) => (prev + 1) % filteredOptions.length);

        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlightIndex((prev) => (prev - 1 + filteredOptions.length) % filteredOptions.length);

        } else if (e.key === 'Enter') {
            e.preventDefault();
            handleSelect(filteredOptions[highlightIndex]);

        } else if (e.key === 'Escape') {
            setIsOpen(false);
        }
    };

    const showDropdown = isOpen;




};


export default DataTypeSelect;