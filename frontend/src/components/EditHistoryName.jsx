import React, { useState, useRef, useEffect } from 'react';
import { axiosJWT } from '../Auth/axios';

function EditHistoryName({ historyId, currentName, onRename }) {
  const [name, setName] = useState(currentName);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axiosJWT.put(`/chat-history/${historyId}/name`, { name });
      onRename(response.data.name || name);
      setEditing(false);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update name');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setName(currentName);
    setEditing(false);
    setError(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  };

  return (
    <div className="flex items-center gap-1.5 w-full">
      {editing ? (
        <div className="flex items-center gap-1 w-full flex-1">
          <input
            ref={inputRef}
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="flex-1 bg-white dark:bg-[#1e1f23] text-legal-darkNavy dark:text-gray-300 text-xs rounded px-2 py-1 border border-legal-navy dark:border-white/20 focus:outline-none focus:ring-1 focus:ring-legal-navy dark:focus:ring-white/40 disabled:opacity-50"
          />
          <button
            onClick={handleSave}
            disabled={loading}
            className="p-1 hover:bg-green-100 dark:hover:bg-green-900/30 rounded text-green-600 dark:text-green-400 transition-all disabled:opacity-50"
            title="Save"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </button>
          <button
            onClick={handleCancel}
            disabled={loading}
            className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-600 dark:text-red-400 transition-all disabled:opacity-50"
            title="Cancel"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      ) : (
        <>
          <span className="flex-1">{name}</span>
          <button
            onClick={() => setEditing(true)}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-legal-navy/10 dark:hover:bg-white/10 rounded text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white transition-all"
            title="Edit name"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
        </>
      )}
      {error && <div className="absolute text-xs text-red-500 dark:text-red-400 mt-8">{error}</div>}
    </div>
  );
}

export default EditHistoryName;
