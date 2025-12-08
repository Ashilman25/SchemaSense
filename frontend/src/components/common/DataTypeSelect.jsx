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

    return (
        <div className = "relative" ref = {containerRef}>
            <div 
                className = "flex items-center bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition"
                onClick = {() => setIsOpen(true)}
            >
                <div className = "pl-3 pr-2 text-gray-400 dark:text-gray-500">
                    <svg className = "w-4 h-4" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M3 5h18M3 12h18M3 19h18" />
                    </svg>
                </div>

                <input 
                    type = "text"
                    value = {inputValue}
                    onChange = {handleInputChange}
                    onKeyDown = {handleKeyDown}
                    onFocus = {() => setIsOpen(true)}
                    placeholder = {placeholder}
                    className = "w-full px-1 pr-10 py-2 text-sm bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none"
                />

                <div className = "absolute right-2 text-gray-400 dark:text-gray-500 pointer-events-none">
                    <svg
                        className = {`w-4 h-4 transition-transform ${showDropdown ? 'rotate-180' : ''}`}
                        fill = "none"
                        stroke = "currentColor"
                        viewBox = "0 0 24 24"
                    >
                        <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </div>

            {showDropdown && (
                <div className = "absolute z-20 mt-1 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-xl overflow-hidden">
                    <div className = "px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-700/50 border-b border-gray-100 dark:border-slate-700">
                        Start typing or pick from the list
                    </div>

                    <div className = "max-h-60 overflow-y-auto">
                        {filteredOptions.map((option, index) => {
                            const isActive = index === highlightIndex;
                            const isCommon = COMMON_TYPES.has(option);

                            return (
                                <button
                                    key = {option}
                                    type = "button"
                                    onMouseEnter = {() => setHighlightIndex(index)}
                                    onMouseDown = {(e) => e.preventDefault()}
                                    onClick = {() => handleSelect(option)}
                                    className = {`w-full flex items-center justify-between px-3 py-2 text-sm transition ${
                                        isActive
                                            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-100'
                                            : 'hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-800 dark:text-gray-100'
                                    }`}
                                >
                                    <div className = "flex items-center space-x-2">
                                        <span className = "font-medium">{option}</span>

                                        {isCommon && (
                                            <span className = "text-[10px] px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 font-semibold">
                                                Popular
                                            </span>
                                        )}
                                    </div>

                                    {isActive && (
                                        <svg className = "w-4 h-4 text-blue-600 dark:text-blue-300" fill = "none" stroke = "currentColor" viewBox = "0 0 24 24">
                                            <path strokeLinecap = "round" strokeLinejoin = "round" strokeWidth = {2} d = "M5 13l4 4L19 7" />
                                        </svg>
                                    )}
                                </button>
                            );
                        })}

                        {filteredOptions.length === 0 && (
                            <div className = "px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                                No matches found
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};


export default DataTypeSelect;