import React, { useState, useRef, useEffect } from 'react';
import DocumentPreviewButton from './DocumentPreviewButton';

const ChatInterface = ({ toggleDraft, toggleSettings }) => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [hasStartedChat, setHasStartedChat] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = () => {
        if (inputValue.trim()) {
            // Add user message
            const userMessage = {
                id: Date.now(),
                type: 'user',
                content: inputValue
            };
            setMessages(prev => [...prev, userMessage]);
            setInputValue('');
            setHasStartedChat(true);

            // Simulate AI response after a short delay
            setTimeout(() => {
                const aiMessage = {
                    id: Date.now() + 1,
                    type: 'assistant',
                    content: 'Hey! I\'m here to help you with your legal queries. Please provide more details about what you need assistance with.'
                };
                setMessages(prev => [...prev, aiMessage]);
            }, 500);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Landing page view - when no messages and chat hasn't started
    if (!hasStartedChat && messages.length === 0) {
        return (
            <div className="w-full max-w-4xl mx-auto px-4 pb-4 flex flex-col justify-center items-center h-full bg-legal-lightGray dark:bg-[#131416]">
                {/* Greeting Section */}
                <div className="flex flex-col items-center justify-center mb-16 opacity-90">
                    <div className="flex items-center gap-3 mb-8">
                        <span className="material-symbols-outlined text-legal-navy dark:text-white" style={{ fontSize: '24px' }}>balance</span>
                        <p className="text-lg text-legal-darkNavy dark:text-gray-300">Hi Pranav</p>
                    </div>
                    <h1 className="text-5xl md:text-6xl font-bold text-legal-darkNavy dark:text-white text-center tracking-tight">
                        Where should we start?
                    </h1>
                </div>

                {/* Input Section */}
                <div className="w-full max-w-2xl">
                    <div className="relative">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={handleKeyPress}
                            className="w-full bg-legal-lightGray dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 text-legal-darkNavy dark:text-gray-300 text-base rounded-2xl py-4 pl-6 pr-32 focus:outline-none focus:ring-1 focus:ring-legal-navy/50 placeholder-legal-gray shadow-lg hover:border-legal-navy dark:hover:border-white/20 transition-colors"
                            placeholder="Ask me anything"
                        />
                        <div className="absolute inset-y-0 right-0 pr-4 flex items-center gap-2">
                            <button className="text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white transition-colors duration-200 p-2 rounded-lg hover:bg-legal-lightGray dark:hover:bg-white/5">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M12 20h9"></path>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                </svg>
                            </button>
                            <button
                                onClick={handleSendMessage}
                                className="text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white transition-colors duration-200 p-2 rounded-lg hover:bg-legal-lightGray dark:hover:bg-white/5"
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Chat view - when messages exist
    return (
        <div className="w-full max-w-4xl mx-auto px-4 pb-4 flex flex-col justify-end h-full bg-legal-lightGray dark:bg-[#131416]">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto py-4 mb-6 flex flex-col items-center">
                <div className="space-y-6 w-full max-w-2xl">
                    {messages.map((message, index) => {
                        const showExtraSpacing = index > 0 && messages[index - 1].type !== message.type;
                        return (
                        <div
                            key={message.id}
                            className={`flex flex-col ${message.type === 'user' ? 'items-end' : 'items-start'} ${
                                showExtraSpacing ? 'pt-4' : ''
                            }`}
                        >
                            {message.type !== 'user' && (
                                <span className="text-[10px] tracking-widest text-gray-500 dark:text-gray-500 light:text-gray-500 font-semibold mb-1 uppercase">
                                    DIKE
                                </span>
                            )}
                            {message.type === 'user' ? (
                                <div className="bg-indigo-100 dark:bg-indigo-950/40 light:bg-indigo-100 text-indigo-900 dark:text-indigo-100 light:text-indigo-900 border border-indigo-300 dark:border-indigo-700/40 light:border-indigo-300 px-6 py-4 rounded-2xl">
                                    <p className="text-sm leading-relaxed">
                                        {message.content}
                                    </p>
                                </div>
                            ) : (
                                <div className="flex flex-col gap-3 w-full">
                                    <p className="text-sm leading-relaxed text-gray-800 dark:text-slate-100 light:text-gray-800">
                                        {message.content}
                                    </p>
                                    <div className="flex items-stretch gap-2 w-full">
                                        <DocumentPreviewButton toggleDraft={toggleDraft} />
                                        <button
                                            className="border border-gray-500 dark:border-gray-500 light:border-gray-500 hover:border-gray-700 dark:hover:border-gray-300 light:hover:border-gray-700 rounded-lg p-3 transition-all hover:bg-gray-200 dark:hover:bg-white/5 light:hover:bg-gray-200 group flex items-center justify-center h-full"
                                            title="Download"
                                        >
                                            <span className="material-symbols-outlined text-gray-600 dark:text-gray-400 light:text-gray-600 group-hover:text-gray-900 dark:group-hover:text-white light:group-hover:text-gray-900" style={{ fontSize: '20px' }}>download</span>
                                        </button>
                                    </div>
                                    {/* Action Buttons */}
                                    <div className="flex gap-2 pt-2 items-center">
                                        <button
                                            onClick={() => {
                                                navigator.clipboard.writeText(message.content);
                                            }}
                                            className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-gray-900 dark:hover:text-white light:hover:text-gray-900 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                            title="Copy"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>content_copy</span>
                                        </button>
                                        <button
                                            className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-green-600 dark:hover:text-green-400 light:hover:text-green-600 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                            title="Like"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>thumb_up</span>
                                        </button>
                                        <button
                                            className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-red-600 dark:hover:text-red-400 light:hover:text-red-600 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                            title="Dislike"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>thumb_down</span>
                                        </button>
                                        <button
                                            className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-blue-600 dark:hover:text-blue-400 light:hover:text-blue-600 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                            title="Regenerate"
                                        >
                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 2.2"></path>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Bar - Modern ChatGPT style */}
            <div className="relative w-full max-w-2xl mx-auto">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full bg-legal-lightGray dark:bg-[#1e1f23] light:bg-legal-lightGray border border-legal-borders dark:border-white/10 light:border-legal-borders text-gray-900 dark:text-gray-300 light:text-gray-900 text-sm rounded-full py-3 pl-6 pr-12 focus:outline-none focus:border-legal-borders dark:focus:border-white/30 light:focus:border-legal-borders focus:ring-1 focus:ring-blue-500/30 placeholder-gray-500 shadow-lg hover:border-legal-borders dark:hover:border-white/20 light:hover:border-legal-borders transition-all duration-200"
                    placeholder="Ask me anything about your projects"
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <button
                        onClick={handleSendMessage}
                        className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-gray-900 dark:hover:text-white light:hover:text-gray-900 transition-colors duration-200 p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
