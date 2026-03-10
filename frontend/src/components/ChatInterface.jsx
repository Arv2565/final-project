import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DocumentPreviewButton from './DocumentPreviewButton';
import LoadingIndicator from './LoadingIndicator';
import CasePdfList from './CasePdfList';
import { getCookie } from '../utils';

const ChatInterface = ({ toggleDraft, toggleSettings, currentSession, onUpdateMessages, isDraftOpen, userId, persistChatToDatabase, createNewChat }) => {


    // Use messages from props, fallback to empty array
    const [messages, setMessages] = useState(currentSession?.messages || []);

    // Internal state for input and UI controls
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStatus, setLoadingStatus] = useState(''); // Text status from server
    const [copiedMessageId, setCopiedMessageId] = useState(null);
    const [toastMessage, setToastMessage] = useState('');
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
    const scrollContainerRef = useRef(null);
    const scrollTimeoutRef = useRef(null);
    const copyResetTimerRef = useRef(null);
    const toastTimerRef = useRef(null);
    const typingTimersRef = useRef({});

    const [typingProgressById, setTypingProgressById] = useState({});
    const [typingCompletedById, setTypingCompletedById] = useState({});

    // Use currentSession?.id directly instead of deriving chatId state
    const chatId = currentSession?.id || null;

    // Track pending message from landing page that should be sent after chat creation
    const pendingMessageRef = useRef(null);

    const adjustTextareaHeight = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
        }
    };

    useEffect(() => {
        adjustTextareaHeight();
    }, [inputValue]);

    const handleScroll = () => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.classList.add('is-scrolling');

            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }

            scrollTimeoutRef.current = setTimeout(() => {
                if (scrollContainerRef.current) {
                    scrollContainerRef.current.classList.remove('is-scrolling');
                }
            }, 3000);
        }
    };

    // WebSocket Reference
    const ws = useRef(null);
    // Messages Reference to avoid stale closures in socket handlers
    const messagesRef = useRef(messages);
    // Reconnect control
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimerRef = useRef(null);
    const intentionalCloseRef = useRef(false);
    const regeneratingMessageIdRef = useRef(null);

    const clearTypingTimer = useCallback((messageId) => {
        if (typingTimersRef.current[messageId]) {
            clearTimeout(typingTimersRef.current[messageId]);
            delete typingTimersRef.current[messageId];
        }
    }, []);

    const startTypingAnimation = useCallback((messageId, fullText) => {
        if (!fullText || typeof fullText !== 'string') {
            setTypingCompletedById((prev) => ({ ...prev, [messageId]: true }));
            return;
        }

        clearTypingTimer(messageId);
        setTypingCompletedById((prev) => ({ ...prev, [messageId]: false }));
        setTypingProgressById((prev) => ({ ...prev, [messageId]: '' }));

        let index = 0;
        // Faster on longer answers so it feels responsive while keeping letter-by-letter effect.
        const step = Math.max(1, Math.ceil(fullText.length / 240));

        const typeNext = () => {
            index = Math.min(index + step, fullText.length);
            const nextChunk = fullText.slice(0, index);
            setTypingProgressById((prev) => ({ ...prev, [messageId]: nextChunk }));

            if (index < fullText.length) {
                typingTimersRef.current[messageId] = setTimeout(typeNext, 16);
                return;
            }

            clearTypingTimer(messageId);
            setTypingCompletedById((prev) => ({ ...prev, [messageId]: true }));
        };

        typeNext();
    }, [clearTypingTimer]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    // Keep messagesRef in sync
    useEffect(() => {
        messagesRef.current = messages;
        scrollToBottom();
    }, [messages, loadingStatus]);

    // Sync messages with parent session
    useEffect(() => {
        Object.keys(typingTimersRef.current).forEach((messageId) => {
            clearTypingTimer(messageId);
        });

        setMessages(currentSession?.messages || []);
        const sessionMessages = Array.isArray(currentSession?.messages) ? currentSession.messages : [];

        // Session history should render fully without replaying typing animation.
        setTypingProgressById(() => {
            const next = {};
            sessionMessages.forEach((msg) => {
                if (msg?.id && typeof msg.content === 'string') {
                    next[msg.id] = msg.content;
                }
            });
            return next;
        });

        setTypingCompletedById(() => {
            const next = {};
            sessionMessages.forEach((msg) => {
                if (msg?.id && typeof msg.content === 'string') {
                    next[msg.id] = true;
                }
            });
            return next;
        });
    }, [currentSession, clearTypingTimer]);

    // Auto-send pending message after chat is created
    useEffect(() => {
        if (chatId && pendingMessageRef.current) {
            const message = pendingMessageRef.current;
            pendingMessageRef.current = null;
            console.log('Auto-sending pending message after chat creation', chatId);

            const isTempChat = chatId.startsWith('temp_');
            // Use ref to get current (unstale) message count
            const isFirstMessage = messagesRef.current.length === 0;

            if (isTempChat && isFirstMessage && persistChatToDatabase) {
                // Need to persist temp chat first
                (async () => {
                    try {
                        const realChatId = await persistChatToDatabase(chatId);
                        // Wait for WebSocket to reconnect with real ID
                        let attempts = 0;
                        while (attempts < 30 && (!ws.current || ws.current.readyState !== WebSocket.OPEN)) {
                            await new Promise(r => setTimeout(r, 100));
                            attempts++;
                        }

                        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                            const userMessage = { id: Date.now(), type: 'user', content: message };
                            const payload = { type: 'query', payload: message, session_id: realChatId };
                            const updatedMessages = [...messagesRef.current, userMessage];
                            setMessages(updatedMessages);
                            if (onUpdateMessages) onUpdateMessages(updatedMessages);
                            setIsLoading(true);
                            setLoadingStatus('Sending...');
                            ws.current.send(JSON.stringify(payload));
                        } else {
                            console.error('WebSocket failed to reconnect after chat persistence');
                            setLoadingStatus('Failed to connect. Please try again.');
                        }
                    } catch (err) {
                        console.error('Failed to auto-send message:', err);
                    }
                })();
            } else if (chatId && ws.current && ws.current.readyState === WebSocket.OPEN) {
                // Send directly with current chatId
                const userMessage = { id: Date.now(), type: 'user', content: message };
                const payload = { type: 'query', payload: message, session_id: chatId };
                const updatedMessages = [...messagesRef.current, userMessage];
                setMessages(updatedMessages);
                if (onUpdateMessages) onUpdateMessages(updatedMessages);
                setIsLoading(true);
                setLoadingStatus('Sending...');
                ws.current.send(JSON.stringify(payload));
            }
        }
    }, [chatId]);

    // WebSocket connect function — extracted so reconnect can call it too
    const connectWebSocket = useCallback((sessionId) => {
        const token = getCookie('auth');
        if (!token || !sessionId || sessionId.startsWith('temp_')) return;

        intentionalCloseRef.current = false;
        const socket = new WebSocket(
            `ws://localhost:8000/api/ws/chat?session_id=${sessionId}&token=${encodeURIComponent(token)}`
        );
        ws.current = socket;

        socket.onopen = () => {
            console.log('WebSocket Connected');
            reconnectAttemptsRef.current = 0; // reset on successful connect
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleServerMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        socket.onclose = (e) => {
            console.log('WebSocket Disconnected', e.code, e.reason);
            if (e.code === 4001) {
                // Auth failure — do not retry
                setIsLoading(false);
                setLoadingStatus('Session expired. Please log in again.');
                return;
            }
            if (!intentionalCloseRef.current && reconnectAttemptsRef.current < 3) {
                const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
                reconnectAttemptsRef.current += 1;
                console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})...`);
                reconnectTimerRef.current = setTimeout(() => connectWebSocket(sessionId), delay);
            } else if (reconnectAttemptsRef.current >= 3) {
                setIsLoading(false);
                setLoadingStatus('Connection lost. Please refresh the page.');
            }
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            setIsLoading(false);
        };
    }, []); // stable — doesn't need deps since it uses refs & args

    // WebSocket Connection Effect
    useEffect(() => {
        // Per-invocation cancel flag — immune to React StrictMode double-invocations.
        // React StrictMode intentionally mounts→unmounts→mounts in dev to surface bugs;
        // using a local 'cancelled' flag means the first invocation's cleanup only
        // cancels ITS OWN pending connection, not the subsequent real one.
        let cancelled = false;

        // Close any existing socket from a previous session
        intentionalCloseRef.current = true;
        clearTimeout(reconnectTimerRef.current);
        if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
            ws.current.close();
            ws.current = null;
        }
        reconnectAttemptsRef.current = 0;

        // Only connect if chatId is NOT temporary (i.e., it's a real database ID)
        const isTempChat = chatId && chatId.startsWith('temp_');
        if (!chatId || isTempChat) {
            console.log('Skipping WebSocket connection for temp chat:', chatId);
            return;
        }

        // 50ms delay lets StrictMode's first effect fully clean up before the
        // second (real) invocation opens the real socket
        const connectTimer = setTimeout(() => {
            if (!cancelled) {
                intentionalCloseRef.current = false; // this invocation owns the socket
                connectWebSocket(chatId);
            }
        }, 50);

        return () => {
            cancelled = true;
            clearTimeout(connectTimer);
            intentionalCloseRef.current = true;
            clearTimeout(reconnectTimerRef.current);
            if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
                ws.current.close();
                ws.current = null;
            }
        };
    }, [chatId, connectWebSocket]); // Re-connect when session changes


    const handleServerMessage = (data) => {
        // Use ref to get latest messages
        const currentMessages = Array.isArray(messagesRef.current) ? messagesRef.current : [];
        let updatedMessages = [...currentMessages];
        switch (data.type) {
            case 'status':
                setLoadingStatus(data.payload);
                setIsLoading(true);
                break;
            case 'case_pdfs': {
                // Handle case PDF paths received from case retrieval
                const pdfPaths = Array.isArray(data.payload) ? data.payload : [];
                if (pdfPaths.length > 0) {
                    console.log(`Received ${pdfPaths.length} case PDF paths`);
                    
                    // Create a message to display the case PDFs using CasePdfList component
                    const casePdfMsg = {
                        id: Date.now(),
                        type: 'assistant',
                        content: null,  // No text content for PDF list
                        payload: { type: 'case_pdfs', paths: pdfPaths },
                        isCasePdfList: true  // Flag to indicate this is a PDF list message
                    };
                    updatedMessages = [...updatedMessages, casePdfMsg];
                    setMessages(updatedMessages);
                    if (onUpdateMessages) onUpdateMessages(updatedMessages);
                }
                break;
            }
            case 'clarification_request': {
                setIsLoading(false);
                setLoadingStatus('');
                const clarificationMsg = {
                    id: Date.now(),
                    type: 'assistant',
                    content: data.payload.question,
                    isClarification: true,
                    payload: data.payload
                };
                updatedMessages = [...updatedMessages, clarificationMsg];
                setMessages(updatedMessages);
                if (onUpdateMessages) onUpdateMessages(updatedMessages);
                startTypingAnimation(clarificationMsg.id, clarificationMsg.content || '');
                break;
            }
            case 'final_result': {
                setIsLoading(false);
                setLoadingStatus('');
                let content = '';
                let documentContent = data.payload.document_content || '';
                if (data.payload.text) {
                    content = data.payload.text;
                } else if (data.payload.data) {
                    content = JSON.stringify(data.payload.data, null, 2);
                }
                const resultMsg = {
                    id: Date.now(),
                    type: 'assistant',
                    content: content,
                    payload: data.payload,
                    documentContent: documentContent
                };

                if (regeneratingMessageIdRef.current) {
                    const targetId = regeneratingMessageIdRef.current;
                    updatedMessages = updatedMessages.map((msg) =>
                        msg.id === targetId
                            ? {
                                ...msg,
                                content,
                                payload: data.payload,
                                documentContent
                            }
                            : msg
                    );
                    startTypingAnimation(targetId, content || '');
                    regeneratingMessageIdRef.current = null;
                } else {
                    updatedMessages = [...updatedMessages, resultMsg];
                    startTypingAnimation(resultMsg.id, content || '');
                }

                setMessages(updatedMessages);
                if (onUpdateMessages) onUpdateMessages(updatedMessages);
                if (documentContent && documentContent.trim() !== '') {
                    toggleDraft(documentContent);
                }
                break;
            }
            case 'error': {
                setIsLoading(false);
                setLoadingStatus('');
                const errorMsg = {
                    id: Date.now(),
                    type: 'system',
                    content: `Error: ${data.payload}`
                };
                updatedMessages = [...updatedMessages, errorMsg];
                setMessages(updatedMessages);
                if (onUpdateMessages) onUpdateMessages(updatedMessages);
                startTypingAnimation(errorMsg.id, errorMsg.content || '');
                break;
            }
            default:
                console.warn('Unknown message type:', data.type);
        }
    };

    const sendMessage = async (messageText, options = {}) => {
        const { forceType = 'auto', clearInput = false, appendUserMessage = true } = options;
        const trimmedMessage = (messageText || '').trim();
        if (!trimmedMessage) return;

        // If chatId is null, we're on the landing page - create a new chat first
        if (!chatId) {
            if (createNewChat) {
                setLoadingStatus('Creating new chat...');
                pendingMessageRef.current = trimmedMessage;
                if (clearInput) setInputValue('');
                createNewChat();
                return;
            }
            console.log('No chat and no createNewChat function available');
            return;
        }

        // For temporary chats, we need to persist first before sending
        const isTempChat = chatId && chatId.startsWith('temp_');
        const isFirstMessage = messagesRef.current.length === 0;

        if (isTempChat && isFirstMessage && persistChatToDatabase) {
            setIsLoading(true);
            setLoadingStatus('Creating chat...');

            try {
                const realChatId = await persistChatToDatabase(chatId);
                let attempts = 0;
                const maxAttempts = 20;

                while (attempts < maxAttempts) {
                    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                        break;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                    attempts++;
                }

                if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
                    console.error('WebSocket failed to reconnect after chat persistence');
                    setIsLoading(false);
                    setLoadingStatus('Failed to connect. Please try again.');
                    return;
                }

                const userMessage = {
                    id: Date.now(),
                    type: 'user',
                    content: trimmedMessage
                };

                const payload = {
                    type: 'query',
                    payload: trimmedMessage,
                    session_id: realChatId,
                };

                const updatedMessages = appendUserMessage
                    ? [...messagesRef.current, userMessage]
                    : [...messagesRef.current];
                setMessages(updatedMessages);
                if (onUpdateMessages) onUpdateMessages(updatedMessages);
                if (clearInput) setInputValue('');
                setIsLoading(true);
                setLoadingStatus('Sending...');

                ws.current.send(JSON.stringify(payload));
            } catch (err) {
                console.error('Failed to persist chat before sending message:', err);
                setIsLoading(false);
                setLoadingStatus('');
            }
            return;
        }

        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        const userMessage = {
            id: Date.now(),
            type: 'user',
            content: trimmedMessage
        };

        const updatedMessages = appendUserMessage
            ? [...messagesRef.current, userMessage]
            : [...messagesRef.current];
        setMessages(updatedMessages);
        if (onUpdateMessages) onUpdateMessages(updatedMessages);
        if (clearInput) setInputValue('');
        setIsLoading(true);
        setLoadingStatus('Sending...');

        const currentMessages = messagesRef.current;
        const lastMessage = currentMessages.length > 0 ? currentMessages[currentMessages.length - 1] : null;
        const isClarificationResponse = lastMessage?.isClarification;

        const payload = {
            type: forceType === 'query' ? 'query' : (isClarificationResponse ? 'clarification_response' : 'query'),
            payload: trimmedMessage,
            session_id: chatId,
        };

        ws.current.send(JSON.stringify(payload));
    };

    const showToast = (message, duration = 1800) => {
        setToastMessage(message);
        if (toastTimerRef.current) {
            clearTimeout(toastTimerRef.current);
        }
        toastTimerRef.current = setTimeout(() => {
            setToastMessage('');
        }, duration);
    };

    const copyTextToClipboard = async (text, messageId) => {
        if (!text) return;

        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
            } else {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                textarea.style.top = '-9999px';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
            }

            setCopiedMessageId(messageId);
            showToast('Copied to clipboard');
            if (copyResetTimerRef.current) {
                clearTimeout(copyResetTimerRef.current);
            }
            copyResetTimerRef.current = setTimeout(() => {
                setCopiedMessageId(null);
            }, 1500);
        } catch (error) {
            console.error('Copy failed:', error);
        }
    };

    const handleRegenerate = async (messageIndex) => {
        const currentMessages = Array.isArray(messagesRef.current) ? messagesRef.current : [];
        const targetMessage = currentMessages[messageIndex];
        if (!targetMessage || targetMessage.type === 'user') {
            return;
        }

        for (let i = messageIndex - 1; i >= 0; i--) {
            const previousMessage = currentMessages[i];
            if (previousMessage?.type === 'user' && previousMessage?.content) {
                regeneratingMessageIdRef.current = targetMessage.id;

                // Clear old assistant response immediately and replace it in-place when new output arrives.
                const clearedMessages = currentMessages.map((msg) =>
                    msg.id === targetMessage.id
                        ? {
                            ...msg,
                            content: '',
                            payload: {},
                            documentContent: ''
                        }
                        : msg
                );
                setMessages(clearedMessages);
                if (onUpdateMessages) onUpdateMessages(clearedMessages);

                showToast('Regenerating...');
                await sendMessage(previousMessage.content, { forceType: 'query', appendUserMessage: false });
                return;
            }
        }
        console.warn('No previous user message found for regenerate action');
    };

    const handleSendMessage = async () => {
        await sendMessage(inputValue, { clearInput: true });
    };

    useEffect(() => {
        return () => {
            Object.keys(typingTimersRef.current).forEach((messageId) => {
                clearTypingTimer(messageId);
            });
            if (copyResetTimerRef.current) {
                clearTimeout(copyResetTimerRef.current);
            }
            if (toastTimerRef.current) {
                clearTimeout(toastTimerRef.current);
            }
        };
    }, [clearTypingTimer]);

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
            // Reset height after sending
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
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
        <div className={`w-full px-4 pb-4 flex flex-col justify-end h-full bg-legal-lightGray dark:bg-[#131416] ${isDraftOpen ? '' : 'max-w-4xl mx-auto'}`}>
            {/* Messages Area */}
            <div
                ref={scrollContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto py-4 mb-6 flex flex-col items-center custom-scrollbar"
            >
                <div className={`space-y-6 w-full ${isDraftOpen ? 'max-w-full' : 'max-w-2xl'}`}>
                    {safeMessages.map((message, index) => {
                        const showExtraSpacing = index > 0 && safeMessages[index - 1].type !== message.type;
                        const isMessageTyping = typingCompletedById[message.id] === false;
                        const renderedContent = isMessageTyping
                            ? (typingProgressById[message.id] || '')
                            : message.content;
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
                                    <div className="bg-indigo-100 dark:bg-indigo-950/40 light:bg-indigo-100 text-indigo-900 dark:text-indigo-100 light:text-indigo-900 border border-indigo-300 dark:border-indigo-700/40 light:border-indigo-300 px-6 py-4 rounded-2xl break-words whitespace-pre-wrap">
                                        <p className="text-sm leading-relaxed text-left break-words">
                                            {message.content}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex flex-col gap-3 w-full">
                                        {renderedContent ? (
                                            <div className="text-sm leading-relaxed text-gray-800 dark:text-slate-100 light:text-gray-800 markdown-content break-words overflow-x-hidden w-full">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {renderedContent}
                                                </ReactMarkdown>
                                                {isMessageTyping && (
                                                    <span className="inline-block w-2 h-4 ml-1 align-middle bg-gray-500 dark:bg-gray-300 animate-pulse" />
                                                )}
                                            </div>
                                        ) : null}
                                        {/* Render CasePdfList for both live websocket and history-loaded messages */}
                                        {Array.isArray(message.payload?.case_pdf_paths) && message.payload.case_pdf_paths.length > 0 ? (
                                            <CasePdfList pdfPaths={message.payload.case_pdf_paths} />
                                        ) : Array.isArray(message.payload?.paths) && message.payload.paths.length > 0 ? (
                                            <CasePdfList pdfPaths={message.payload.paths} />
                                        ) : null}
                                        {/* Document Preview & Download Buttons */}
                                        {message.documentContent && message.documentContent.trim() !== '' && !isMessageTyping && (
                                            <div className="flex items-stretch gap-2 w-full mt-3">
                                                <DocumentPreviewButton
                                                    toggleDraft={() => toggleDraft(message.documentContent)}
                                                />
                                                <button
                                                    onClick={() => {
                                                        const blob = new Blob([message.documentContent], { type: 'text/markdown' });
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        a.download = 'document.md';
                                                        document.body.appendChild(a);
                                                        a.click();
                                                        document.body.removeChild(a);
                                                        URL.revokeObjectURL(url);
                                                    }}
                                                    className="border border-gray-500 dark:border-gray-500 light:border-gray-500 hover:border-gray-700 dark:hover:border-gray-300 light:hover:border-gray-700 rounded-lg p-3 transition-all hover:bg-gray-200 dark:hover:bg-white/5 light:hover:bg-gray-200 group flex items-center justify-center h-full"
                                                    title="Download"
                                                >
                                                    <span className="material-symbols-outlined text-gray-600 dark:text-gray-400 light:text-gray-600 group-hover:text-gray-900 dark:group-hover:text-white light:group-hover:text-gray-900" style={{ fontSize: '20px' }}>download</span>
                                                </button>
                                            </div>
                                        )}
                                        {/* Action Buttons */}
                                        {renderedContent && !isMessageTyping && (
                                            <div className="flex gap-2 pt-2 items-center">
                                                <button
                                                    onClick={() => copyTextToClipboard(message.content, message.id)}
                                                    className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-gray-900 dark:hover:text-white light:hover:text-gray-900 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                                    title={copiedMessageId === message.id ? 'Copied' : 'Copy'}
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
                                                        {copiedMessageId === message.id ? 'check' : 'content_copy'}
                                                    </span>
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
                                                    onClick={() => handleRegenerate(index)}
                                                    disabled={isLoading}
                                                    className="text-gray-600 dark:text-gray-400 light:text-gray-600 hover:text-blue-600 dark:hover:text-blue-400 light:hover:text-blue-600 transition-colors p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 light:hover:bg-gray-200 flex items-center justify-center"
                                                    title="Regenerate"
                                                >
                                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                        <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 2.2"></path>
                                                    </svg>
                                                </button>
                                            </div>
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
            <div className={`relative w-full mx-auto bg-legal-lightGray dark:bg-[#1e1f23] light:bg-legal-lightGray border border-legal-borders dark:border-white/10 light:border-legal-borders rounded-2xl shadow-lg hover:border-legal-borders dark:hover:border-white/20 light:hover:border-legal-borders transition-all duration-200 ${isDraftOpen ? 'max-w-full' : 'max-w-2xl'}`}>
                <textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyPress}
                    rows={1}
                    className="w-full bg-transparent text-gray-900 dark:text-gray-300 light:text-gray-900 text-sm rounded-2xl py-3 pl-6 pr-12 focus:outline-none resize-none custom-scrollbar"
                    placeholder="Ask me anything about your projects"
                    style={{ minHeight: '44px', maxHeight: '200px' }}
                />
                <div className="absolute bottom-1 right-2 p-1">
                    <button
                        onClick={handleSendMessage}
                        disabled={!inputValue.trim() || isLoading}
                        className={`p-2 rounded-lg transition-colors duration-200 ${inputValue.trim()
                            ? 'bg-legal-navy/10 text-legal-navy dark:bg-white/10 dark:text-white hover:bg-legal-navy/20 dark:hover:bg-white/20'
                            : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                            }`}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>

            {toastMessage && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg bg-legal-darkNavy/95 text-white text-sm shadow-lg border border-white/10">
                    {toastMessage}
                </div>
            )}
        </div>
    );
};

export default ChatInterface;
