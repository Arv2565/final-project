import React, { useState, useEffect } from 'react';

const DraftBuilder = ({ onClose, content = '', onContentChange }) => {
    const [isEditMode, setIsEditMode] = useState(false);
    const [editableContent, setEditableContent] = useState(content);

    // Sync editableContent when content prop changes
    useEffect(() => {
        setEditableContent(content);
    }, [content]);

    const handleContentChange = (e) => {
        const newContent = e.target.value;
        setEditableContent(newContent);
        if (onContentChange) {
            onContentChange(newContent);
        }
    };

    const toggleEditMode = () => {
        setIsEditMode((prev) => !prev);
    };

    return (
        <div className="bg-white dark:bg-[#0d0e10] rounded-3xl p-6 flex flex-col h-full shadow-2xl relative animate-in slide-in-from-right duration-300 border border-legal-borders dark:border-white/5 font-sans">
            {/* Header */}
            <div className="flex justify-between items-center mb-4 border-b border-legal-borders dark:border-white/10 pb-4">
                <div className="flex items-center gap-2">
                    <div className="bg-legal-lightGray dark:bg-white/10 rounded p-1">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-legal-darkNavy dark:text-white">
                            <path d="M12 20h9"></path>
                            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold text-legal-darkNavy dark:text-gray-100">Draft Builder</h2>
                </div>
                <div className="flex items-center gap-2">
                    {/* Edit/Preview Toggle */}
                    <button
                        onClick={toggleEditMode}
                        className={`text-sm border rounded-full px-4 py-1.5 transition-colors font-medium ${
                            isEditMode
                                ? 'bg-legal-darkNavy dark:bg-white text-white dark:text-[#0d0e10] border-legal-darkNavy dark:border-white'
                                : 'border-legal-borders dark:border-white/20 text-legal-darkNavy dark:text-gray-300 hover:bg-legal-lightGray dark:hover:bg-white/5'
                        }`}
                    >
                        {isEditMode ? 'Preview' : 'Edit'}
                    </button>
                    <button className="text-sm border border-legal-borders dark:border-white/20 rounded-full px-4 py-1.5 hover:bg-legal-lightGray dark:hover:bg-white/5 transition-colors font-medium text-legal-darkNavy dark:text-gray-300">
                        Export as PDF
                    </button>
                    <button onClick={onClose} className="p-2 hover:bg-legal-lightGray dark:hover:bg-white/10 rounded-full transition-colors">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-legal-gray dark:text-gray-400">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar w-full min-w-0">
                {editableContent && editableContent.trim() !== '' ? (
                    isEditMode ? (
                        /* Edit Mode - Textarea */
                        <textarea
                            value={editableContent}
                            onChange={handleContentChange}
                            className="w-full h-full min-h-[400px] p-4 rounded-lg border border-legal-borders dark:border-white/10 bg-legal-lightGray/50 dark:bg-white/5 text-legal-darkNavy dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-legal-darkNavy/20 dark:focus:ring-white/20 resize-none"
                            style={{ fontFamily: 'Arial, Helvetica, sans-serif', fontSize: '14px', lineHeight: '1.6' }}
                            placeholder="Edit your document content here..."
                        />
                    ) : (
                        /* Preview Mode - Plain text to preserve exact legal formatting */
                        <div
                            className="draft-markdown-content w-full text-legal-darkNavy dark:text-gray-300 bg-transparent"
                            style={{ fontFamily: 'Arial, Helvetica, sans-serif' }}
                        >
                            {editableContent}
                        </div>
                    )
                ) : (
                    <div className="flex items-center justify-center h-full">
                        <p className="text-gray-500 dark:text-gray-400 italic text-center">
                            No document content available.<br />
                            <span className="text-sm">Generate a document to see it here.</span>
                        </p>
                    </div>
                )}
            </div>

            {/* Custom styles for markdown rendering */}
            <style>{`
                .draft-markdown-content {
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 0.95rem;
                    line-height: 1.6;
                    background: transparent;
                    word-wrap: break-word;
                    overflow-wrap: anywhere;
                    word-break: break-word;
                    white-space: pre-wrap;
                    max-width: 100%;
                    overflow-x: hidden;
                }

                .draft-markdown-content * {
                    font-family: inherit;
                }

                .draft-markdown-content li::marker {
                    font-family: inherit;
                }
                
                .draft-markdown-content h1,
                .draft-markdown-content h2,
                .draft-markdown-content h3,
                .draft-markdown-content h4,
                .draft-markdown-content h5,
                .draft-markdown-content h6 {
                    font-weight: 700;
                    margin-top: 0.9em;
                    margin-bottom: 0.35em;
                    line-height: 1.25;
                }
                
                .draft-markdown-content h1 { font-size: 1.75rem; }
                .draft-markdown-content h2 { font-size: 1.5rem; }
                .draft-markdown-content h3 { font-size: 1.25rem; }
                .draft-markdown-content h4 { font-size: 1.125rem; }
                
                .draft-markdown-content p {
                    margin: 0;
                }

                .draft-markdown-content p + p {
                    margin-top: 0.25em;
                }
                
                .draft-markdown-content ul,
                .draft-markdown-content ol {
                    margin: 0.25em 0;
                    padding-left: 1.5em;
                }
                
                .draft-markdown-content ol {
                    list-style-type: decimal;
                }
                
                .draft-markdown-content ul {
                    list-style-type: disc;
                }
                
                .draft-markdown-content li {
                    margin: 0;
                    padding-left: 0.25em;
                }

                .draft-markdown-content li + li {
                    margin-top: 0.1em;
                }
                
                .draft-markdown-content li > p {
                    margin: 0;
                    display: inline;
                }
                
                .draft-markdown-content li > ul,
                .draft-markdown-content li > ol {
                    margin-top: 0.25em;
                    margin-bottom: 0.25em;
                }
                
                .draft-markdown-content blockquote {
                    border-left: 4px solid #d1d5db;
                    padding-left: 1em;
                    margin: 0.5em 0;
                    font-style: italic;
                    color: #6b7280;
                }
                
                .draft-markdown-content code {
                    background-color: transparent;
                    padding: 0;
                    border-radius: 0;
                    font-size: 0.9em;
                    white-space: pre-wrap;
                    overflow-wrap: anywhere;
                    word-break: break-word;
                }
                
                .draft-markdown-content pre {
                    background-color: transparent;
                    padding: 0;
                    border-radius: 0;
                    overflow-x: hidden;
                    margin: 0.5em 0;
                    white-space: pre-wrap;
                    line-height: 1.25;
                }
                
                .draft-markdown-content pre code {
                    background: none;
                    padding: 0;
                    white-space: pre-wrap;
                    overflow-wrap: anywhere;
                    word-break: break-word;
                }
                
                .draft-markdown-content table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                    font-size: 1rem;
                    table-layout: fixed;
                }
                
                .draft-markdown-content th,
                .draft-markdown-content td {
                    border: 1px solid #d1d5db;
                    padding: 0.5em 0.75em;
                    text-align: left;
                    overflow-wrap: anywhere;
                    word-break: break-word;
                }
                
                .draft-markdown-content th {
                    background-color: transparent;
                    font-weight: 600;
                }
                
                .draft-markdown-content hr {
                    border: none;
                    border-top: 1px solid #d1d5db;
                    margin: 1.25em 0;
                }
                
                .draft-markdown-content a {
                    color: #2563eb;
                    text-decoration: underline;
                }
                
                .draft-markdown-content a:hover {
                    color: #1d4ed8;
                }
                
                .dark .draft-markdown-content blockquote {
                    border-left-color: #4b5563;
                    color: #9ca3af;
                }
                
                .dark .draft-markdown-content code {
                    background-color: transparent;
                }
                
                .dark .draft-markdown-content pre {
                    background-color: transparent;
                }
                
                .dark .draft-markdown-content th,
                .dark .draft-markdown-content td {
                    border-color: #4b5563;
                }
                
                .dark .draft-markdown-content th {
                    background-color: transparent;
                }
                
                .dark .draft-markdown-content hr {
                    border-top-color: #4b5563;
                }
            `}</style>
        </div>
    );
};

export default DraftBuilder;
