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

    /**
     * Handle PDF download by calling the backend endpoint
     */
    const handleDownloadPdf = async (filePath) => {
        try {
            const filename = getFilenameFromPath(filePath);
            const response = await axiosJWT.get('files/download', {
                params: { file_path: filePath },
                responseType: 'blob',
            });

            const contentType = response.headers?.['content-type'] || '';
            if (!contentType.includes('application/pdf')) {
                throw new Error(`Unexpected response type: ${contentType}`);
            }

            // Create a blob URL so browser saves exact binary payload
            const blob = new Blob([response.data], { type: 'application/pdf' });
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

    const downloadButtonClasses = `
        px-3 py-2 bg-legal-navy dark:bg-blue-600 hover:bg-legal-darkNavy dark:hover:bg-blue-700
        text-white rounded-md transition-colors text-sm font-medium
        flex items-center gap-1 whitespace-nowrap
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

                                <button
                                    onClick={() => handleDownloadPdf(pdfPath)}
                                    className={downloadButtonClasses}
                                    title={`Download ${filename}`}
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                                        download
                                    </span>
                                    <span>Download</span>
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default CasePdfList;
