import React, { useState } from 'react';
import { axiosJWT } from '../Auth/axios';

/**
 * CasePdfList Component
 * 
 * Displays a list of case PDF files retrieved from the case retriever.
 * Allows users to download PDF files with an expandable accordion UI.
 * 
 * Props:
 *   - pdfPaths: Array of PDF file paths (e.g., ['tool/data/case_files/A Raja.pdf'])
 */
const CasePdfList = ({ pdfPaths = [] }) => {
    const [isExpanded, setIsExpanded] = useState(true);

    if (!pdfPaths || pdfPaths.length === 0) {
        return null;
    }

    /**
     * Extract filename from a full file path
     * Example: 'tool/data/case_files/A Raja.pdf' -> 'A Raja.pdf'
     */
    const getFilenameFromPath = (path) => {
        if (typeof path !== 'string') return 'Unknown';
        return path.split('/').pop() || 'Unknown';
    };

    const fetchPdfBlob = async (filePath) => {
        const response = await axiosJWT.get('files/download', {
            params: { file_path: filePath },
            responseType: 'blob',
        });

        const contentType = response.headers?.['content-type'] || '';
        if (!contentType.includes('application/pdf')) {
            throw new Error(`Unexpected response type: ${contentType}`);
        }

        return new Blob([response.data], { type: 'application/pdf' });
    };

    /**
     * Handle PDF download by calling the backend endpoint
     */
    const handleDownloadPdf = async (filePath) => {
        try {
            const filename = getFilenameFromPath(filePath);
            const blob = await fetchPdfBlob(filePath);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            console.log(`Downloaded PDF: ${filename}`);
        } catch (error) {
            console.error(`Failed to download PDF (${filePath}):`, error);
            alert(`Failed to download PDF: ${getFilenameFromPath(filePath)}`);
        }
    };

    /**
     * Open PDF preview in a new browser tab
     */
    const handleOpenPdfInNewTab = async (filePath) => {
        const previewTab = window.open('', '_blank', 'noopener,noreferrer');

        if (!previewTab) {
            alert('Popup blocked. Please allow popups and try again.');
            return;
        }

        try {
            const blob = await fetchPdfBlob(filePath);
            const url = URL.createObjectURL(blob);
            previewTab.location.href = url;

            // Give the new tab enough time to resolve URL before cleanup.
            setTimeout(() => URL.revokeObjectURL(url), 60_000);
        } catch (error) {
            previewTab.close();
            console.error(`Failed to open PDF (${filePath}):`, error);
            alert(`Failed to open PDF: ${getFilenameFromPath(filePath)}`);
        }
    };

    const accordionHeaderClasses = `
        w-full flex items-center justify-between p-3 bg-gradient-to-r from-legal-navy to-legal-darkNavy 
        dark:from-gray-800 dark:to-gray-900 rounded-t-lg 
        hover:shadow-md transition-shadow cursor-pointer text-white
    `;

    const accordionContentClasses = `
        bg-legal-lightGray dark:bg-gray-800/50 rounded-b-lg p-4 space-y-2
    `;

    const pdfItemClasses = `
        flex items-center justify-between p-3 bg-white dark:bg-gray-700/50 
        rounded-lg border border-legal-borders dark:border-gray-600 
        hover:border-legal-navy dark:hover:border-blue-400 transition-all group
    `;

    const openButtonClasses = `
        border border-legal-borders dark:border-gray-500 hover:border-legal-navy dark:hover:border-gray-300
        rounded-lg px-3 py-2 transition-all hover:bg-legal-lightGray dark:hover:bg-white/5
        group flex items-center justify-center gap-2 h-full
    `;

    const downloadButtonClasses = `
        border border-legal-borders dark:border-gray-500 hover:border-legal-navy dark:hover:border-gray-300
        rounded-lg p-2 transition-all hover:bg-legal-lightGray dark:hover:bg-white/5
        group flex items-center justify-center h-full
    `;

    return (
        <div className="w-full my-3 border border-legal-borders dark:border-gray-600 rounded-lg overflow-hidden">
            {/* Accordion Header */}
            <div
                className={accordionHeaderClasses}
                onClick={() => setIsExpanded(!isExpanded)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        setIsExpanded(!isExpanded);
                    }
                }}
            >
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
                        {isExpanded ? 'expand_less' : 'expand_more'}
                    </span>
                    <span className="font-semibold">
                        Retrieved Case PDFs ({pdfPaths.length})
                    </span>
                </div>
            </div>

            {/* Accordion Content */}
            {isExpanded && (
                <div className={accordionContentClasses}>
                    {pdfPaths.map((pdfPath, index) => {
                        const filename = getFilenameFromPath(pdfPath);
                        return (
                            <div key={`pdf-${index}`} className={pdfItemClasses}>
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <span
                                        className="material-symbols-outlined text-legal-navy dark:text-blue-400 group-hover:text-legal-darkNavy dark:group-hover:text-blue-300 flex-shrink-0"
                                        style={{ fontSize: '18px' }}
                                    >
                                        picture_as_pdf
                                    </span>
                                    <span className="text-sm text-legal-darkGray dark:text-gray-300 truncate font-medium">
                                        {filename}
                                    </span>
                                </div>

                                <div className="flex items-stretch gap-2 ml-3">
                                    <button
                                        onClick={() => handleOpenPdfInNewTab(pdfPath)}
                                        className={openButtonClasses}
                                        title={`Open ${filename} in new tab`}
                                        aria-label={`Open ${filename} in new tab`}
                                    >
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-legal-gray dark:text-gray-400 group-hover:text-legal-darkNavy dark:group-hover:text-white">
                                            <path d="M12 20h9"></path>
                                            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                        </svg>
                                        <span className="text-sm text-legal-gray dark:text-gray-400 group-hover:text-legal-darkNavy dark:group-hover:text-white whitespace-nowrap">
                                            Open PDF
                                        </span>
                                    </button>

                                    <button
                                        onClick={() => handleDownloadPdf(pdfPath)}
                                        className={downloadButtonClasses}
                                        title={`Download ${filename}`}
                                        aria-label={`Download ${filename}`}
                                    >
                                        <span className="material-symbols-outlined text-legal-gray dark:text-gray-400 group-hover:text-legal-darkNavy dark:group-hover:text-white" style={{ fontSize: '18px' }}>
                                            download
                                        </span>
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default CasePdfList;
