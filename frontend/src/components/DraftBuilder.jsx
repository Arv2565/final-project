import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const DraftBuilder = ({ onClose, content = '' }) => {
    return (
        <div className="bg-white dark:bg-[#0d0e10] rounded-3xl p-6 flex flex-col h-full shadow-2xl relative animate-in slide-in-from-right duration-300 border border-legal-borders dark:border-white/5">
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

            {/* Editable Content */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar w-full">
                {content && content.trim() !== '' ? (
                    <div
                        className="prose prose-lg max-w-none w-full break-words text-legal-darkNavy dark:text-gray-300"
                        style={{ fontFamily: 'Times New Roman, serif' }}
                    >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {content}
                        </ReactMarkdown>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full">
                        <p className="text-gray-500 dark:text-gray-400 italic text-center">
                            No document content available.<br />
                            <span className="text-sm">Generate a document to see it here.</span>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DraftBuilder;
