import React from 'react';

const DraftBuilder = ({ onClose }) => {
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
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                <div
                    className="prose prose-lg max-w-none focus:outline-none text-legal-darkNavy dark:text-gray-300"
                    style={{ fontFamily: 'Times New Roman, serif' }}
                    contentEditable
                    suppressContentEditableWarning
                >
                    <h1 className="text-3xl font-bold text-legal-navy dark:text-legal-lightGold mb-4">Legal Analysis of Public Urination and Lying to Police in India</h1>
                    <p className="mb-4 text-legal-gray dark:text-gray-400">
                        This analysis addresses the potential legal consequences in India for urinating on a public road and subsequently lying to the police who witnessed the act.
                    </p>

                    <h3 className="text-xl font-bold text-legal-darkNavy dark:text-gray-100 mt-6 mb-2">Direct Answer:</h3>
                    <p className="mb-4">
                        You could face charges under multiple sections of the Indian Penal Code (IPC) for urinating in public and for lying to the police. The most relevant charges are likely under Section 294 (for obscene acts) and Section 182 (for giving false information).
                    </p>

                    <h3 className="text-xl font-bold text-legal-darkNavy dark:text-gray-100 mt-6 mb-2">Legal Provisions and Applicability:</h3>

                    <h4 className="text-lg font-bold text-legal-navy dark:text-gray-200 mt-4 mb-2">Indian Penal Code Section 294 - Obscene Acts and Songs:</h4>
                    <ul className="list-disc pl-5 mb-4 space-y-2">
                        <li>
                            <strong className="text-gray-100">Applicability:</strong> This section applies because urinating on a public road can be considered an "obscene act" performed in a public place. The police witnessing the act (Event E2) suggests that it could cause annoyance to others, fulfilling a key element of this offense.
                        </li>
                        <li>
                            <strong className="text-gray-100">Evidence:</strong> The act of urinating on a public road (F1, E1) directly relates to this provision. Police observation (E2) supports the likelihood of annoyance.
                        </li>
                    </ul>

                    <h4 className="text-lg font-bold text-gray-200 mt-4 mb-2">Indian Penal Code Section 182 - False Information:</h4>
                    <ul className="list-disc pl-5 mb-4 space-y-2">
                        <li>
                            <strong className="text-gray-100">Applicability:</strong> This section is highly applicable as you "lied to the police" (F2, E3) after being witnessed urinating. This constitutes giving false information to a public servant.
                        </li>
                        <li>
                            <strong className="text-gray-100">Evidence:</strong> The act of lying to the police (F2, E3), who are public servants (F5), directly supports this charge.
                        </li>
                    </ul>
                    <p className="mt-8 text-gray-500 italic text-sm">
                        Start typing here to edit this draft...
                    </p>
                </div>
            </div>
        </div>
    );
};

export default DraftBuilder;
