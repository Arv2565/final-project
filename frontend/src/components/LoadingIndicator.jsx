import React from 'react';

const blinkingStyle = `
    @keyframes blink {
        0%, 49% {
            opacity: 0.3;
        }
        50%, 100% {
            opacity: 1;
        }
    }
    .blink-animation {
        animation: blink 1s infinite;
    }
`;

const LoadingIndicator = ({ loadingStage }) => (
    <div className="mb-3 flex items-center gap-2">
        <style>{blinkingStyle}</style>
        <span className="material-symbols-outlined text-gray-500 dark:text-gray-400 blink-animation" style={{ fontSize: '18px' }}>balance</span>
        {loadingStage === 1 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
                processing query
            </p>
        )}
        {loadingStage === 2 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
                extracting data
            </p>
        )}
        {loadingStage === 3 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
                finalizing content
            </p>
        )}
    </div>
);

export default LoadingIndicator;
