import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DocumentPreviewButton from './DocumentPreviewButton';
import LoadingIndicator from './LoadingIndicator';

const ChatInterface = ({ toggleDraft, toggleSettings, currentSession, onUpdateMessages }) => {


    // Use messages from props, fallback to empty array
    const messages = currentSession?.messages || [];

    // Internal state for input and UI controls
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStatus, setLoadingStatus] = useState(''); // Text status from server
    const messagesEndRef = useRef(null);

    // WebSocket Reference
    const ws = useRef(null);
    // Messages Reference to avoid stale closures in socket handlers
    const messagesRef = useRef(messages);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    // Keep messagesRef in sync
    useEffect(() => {
        messagesRef.current = messages;
        scrollToBottom();
    }, [messages, loadingStatus]);

    // WebSocket Connection Effect
    useEffect(() => {
        // Close existing connection if any
        if (ws.current) {
            ws.current.close();
        }

        // Initialize WebSocket
        const socket = new WebSocket('ws://localhost:8000/api/ws/chat');
        ws.current = socket;

        socket.onopen = () => {
            console.log('WebSocket Connected');
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleServerMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        socket.onclose = () => {
            console.log('WebSocket Disconnected');
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            setIsLoading(false);
            setLoadingStatus('');
        };

        // Cleanup on unmount or session change
        return () => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.close();
            }
        };
    }, [currentSession?.id]); // Re-connect when session ID changes

    const handleServerMessage = (data) => {
        // Use ref to get latest messages
        const currentMessages = Array.isArray(messagesRef.current) ? messagesRef.current : [];

        switch (data.type) {
            case 'status':
                setLoadingStatus(data.payload);
                setIsLoading(true);
                break;

            case 'clarification_request':
                setIsLoading(false);
                setLoadingStatus('');
                // Add clarification question as an assistant message
                const clarificationMsg = {
                    id: Date.now(),
                    type: 'assistant',
                    content: data.payload.question,
                    isClarification: true,
                    payload: data.payload // Store full payload if needed
                };
                if (onUpdateMessages) {
                    onUpdateMessages([...currentMessages, clarificationMsg]);
                }
                break;

            case 'final_result':
                setIsLoading(false);
                setLoadingStatus('');

                let content = '';
                if (data.payload.text) {
                    content = data.payload.text;
                } else if (data.payload.data) {
                    // Format structured data/JSON as a string for now, or handled by a specific renderer
                    // For the "final outputs payload should be displayed" requirement
                    content = JSON.stringify(data.payload.data, null, 2);

                    // If it's a procedural workflow, we might want to format it nicely
                    if (data.payload.workflow === 'procedural') {
                        // Construct a friendly summary if possible, otherwise just dump the JSON
                        // The user said "final outputs payload should be displayed"
                        // We'll stick to text for the main bubble
                    }
                }

                const resultMsg = {
                    id: Date.now(),
                    type: 'assistant',
                    content: content,
                    payload: data.payload // Store full payload for custom rendering if needed
                };

                // Functional update: need to get previous messages.
                // Since we don't have direct access to setMessages (it's in parent), 
                // we rely on 'messages' prop being fresh due to re-renders.
                // However, onUpdateMessages expects the NEW VALUE, not a callback usually, 
                // unless the parent handles it. Home.jsx calls updateSessionMessages(id, msgs).
                // Let's assume we need to pass the full array.
                if (onUpdateMessages) {
                    onUpdateMessages([...currentMessages, resultMsg]);
                }
                break;

            case 'error':
                setIsLoading(false);
                setLoadingStatus('');
                const errorMsg = {
                    id: Date.now(),
                    type: 'system', // or assistant
                    content: `Error: ${data.payload}`
                };
                if (onUpdateMessages) {
                    onUpdateMessages([...currentMessages, errorMsg]);
                }
                break;

            default:
                console.warn('Unknown message type:', data.type);
        }
    };

    const handleSendMessage = () => {
        if (!inputValue.trim()) return;

        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            // Optionally try to reconnect or alert user
            return;
        }

        const userMessage = {
            id: Date.now(),
            type: 'user',
            content: inputValue
        };

        // Update UI immediately
        onUpdateMessages([...messages, userMessage]);
        setInputValue('');
        setIsLoading(true);
        setLoadingStatus('Sending...');

        // Check if we are responding to a clarification (naive check: last message was a clarification)
        // Or better, let the backend state handle it. The backend expects 'clarification_response' 
        // if it's waiting, or 'query' if it's new. 
        // BUT, the backend `socket_handlers.py` logic checks `current_state.get("pending_clarification")`.
        // The Frontend doesn't strictly know the backend state unless we track it.
        // However, the PROMPT said "when a clarification question is asked... the next msg should be clarification response"

        // Let's determine the type based on the last message
        const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
        const isClarificationResponse = lastMessage?.isClarification;

        const payload = {
            type: isClarificationResponse ? 'clarification_response' : 'query',
            payload: inputValue
        };

        ws.current.send(JSON.stringify(payload));
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Landing page view - when no messages and chat hasn't started
    // We check messages.length directly. Ensure messages is an array.
    const safeMessages = Array.isArray(messages) ? messages : [];

    if (safeMessages.length === 0) {
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
                    {safeMessages.map((message, index) => {
                        const showExtraSpacing = index > 0 && safeMessages[index - 1].type !== message.type;
                        return (
                            <div
                                key={message.id}
                                className={`flex flex-col ${message.type === 'user' ? 'items-end' : 'items-start'} ${showExtraSpacing ? 'pt-4' : ''
                                    }`}
                            >
                                {message.type !== 'user' && (
                                    <>
                                        <span className="text-[10px] tracking-widest text-gray-500 dark:text-gray-500 light:text-gray-500 font-semibold mb-1 uppercase">
                                            DIKE
                                        </span>
                                        {/* Loading Indicator */}
                                        {isLoading && messages[messages.length - 1]?.id === message.id && (
                                            <div className="flex items-center gap-2 text-gray-500 text-sm">
                                                <LoadingIndicator />
                                                <span>{loadingStatus}</span>
                                            </div>
                                        )}
                                    </>
                                )}
                                {message.type === 'user' ? (
                                    <div className="bg-indigo-100 dark:bg-indigo-950/40 light:bg-indigo-100 text-indigo-900 dark:text-indigo-100 light:text-indigo-900 border border-indigo-300 dark:border-indigo-700/40 light:border-indigo-300 px-6 py-4 rounded-2xl">
                                        <p className="text-sm leading-relaxed">
                                            {message.content}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex flex-col gap-3 w-full">
                                        {message.content && (
                                            <>
                                                <div className="text-sm leading-relaxed text-gray-800 dark:text-slate-100 light:text-gray-800 markdown-content">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {message.content}
                                                    </ReactMarkdown>
                                                </div>
                                                {/* Document Generation - Currently Disabled
                                                <div className="flex items-stretch gap-2 w-full">
                                                    <DocumentPreviewButton toggleDraft={toggleDraft} />
                                                    <button
                                                        className="border border-gray-500 dark:border-gray-500 light:border-gray-500 hover:border-gray-700 dark:hover:border-gray-300 light:hover:border-gray-700 rounded-lg p-3 transition-all hover:bg-gray-200 dark:hover:bg-white/5 light:hover:bg-gray-200 group flex items-center justify-center h-full"
                                                        title="Download"
                                                    >
                                                        <span className="material-symbols-outlined text-gray-600 dark:text-gray-400 light:text-gray-600 group-hover:text-gray-900 dark:group-hover:text-white light:group-hover:text-gray-900" style={{ fontSize: '20px' }}>download</span>
                                                    </button>
                                                </div>
                                                */}
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
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                    {isLoading && (
                        <div className="flex flex-col items-start pt-4 w-full">
                            <span className="text-[10px] tracking-widest text-gray-500 dark:text-gray-500 light:text-gray-500 font-semibold mb-1 uppercase">
                                DIKE
                            </span>
                            <div className="flex items-center gap-2 text-gray-500 text-sm">
                                <LoadingIndicator />
                                <span className="animate-pulse">{loadingStatus || 'Thinking...'}</span>
                            </div>
                        </div>
                    )}
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
