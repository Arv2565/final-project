import React, { useState, useEffect, useContext } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { AuthContext } from '../Auth/AuthContext';
import { axiosJWT } from '../Auth/axios';

const Layout = () => {
    const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);
    const [toggleSettingsCallback, setToggleSettingsCallback] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const [loadedMessages, setLoadedMessages] = useState({}); // { chatId: messages[] }
    const navigation = useNavigate();
    const location = useLocation();
    const { user, isLoggedIn } = useContext(AuthContext);

    // Fetch chat sessions from the DB on mount / login
    useEffect(() => {
        if (!isLoggedIn || !user) return;

        const fetchSessions = async () => {
            try {
                const res = await axiosJWT.get('/chat-history/');
                const chats = res.data;
                if (Array.isArray(chats) && chats.length > 0) {
                    const mapped = chats.map(c => ({
                        id: c.id,
                        title: c.title || 'New Chat',
                        messages: [],
                        timestamp: c.updated_at,
                    }));
                    setSessions(mapped);
                    setCurrentSessionId(mapped[0].id);
                } else {
                    setSessions([]);
                    setCurrentSessionId(null);
                }
            } catch (err) {
                console.error('Failed to fetch chat sessions', err);
                setSessions([]);
                setCurrentSessionId(null);
            }
        };

        fetchSessions();
    }, [isLoggedIn, user]);

    // Load messages when the active session changes
    useEffect(() => {
        if (!currentSessionId || !isLoggedIn) return;

        // Skip fetching if already loaded
        if (loadedMessages[currentSessionId]) return;

        // Skip fetching for temporary chats (not yet persisted to database)
        const isTempChat = currentSessionId && currentSessionId.startsWith('temp_');
        if (isTempChat) {
            console.log('Skipping fetch for temp chat:', currentSessionId);
            return;
        }

        const fetchMessages = async () => {
            try {
                const res = await axiosJWT.get(`/chat-history/${currentSessionId}`);
                const chat = res.data;
                const msgs = (chat.messages || []).map(m => ({
                    id: m.id,
                    type: m.sender, // DB uses "sender", frontend uses "type"
                    content: m.content,
                    documentContent: m.document?.content || '',
                    isClarification: m.metadata?.clarification || false,
                    payload: m.metadata || {},
                }));

                setLoadedMessages(prev => ({ ...prev, [currentSessionId]: msgs }));
                setSessions(prev => prev.map(s =>
                    s.id === currentSessionId ? { ...s, messages: msgs } : s
                ));
            } catch (err) {
                console.error('Failed to fetch messages for chat', currentSessionId, err);
            }
        };

        fetchMessages();
    }, [currentSessionId, isLoggedIn]);

    const toggleSidebar = () => {
        setIsSidebarExpanded(!isSidebarExpanded);
    };

    const handleSettingsClick = () => {
        if (toggleSettingsCallback) {
            toggleSettingsCallback();
        }
    };

    const createNewChat = () => {
        // Create chat locally with temporary ID - no DB persistence yet
        // Database persistence happens on first message
        const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newSession = {
            id: tempId,
            title: 'New Chat',
            messages: [],
            timestamp: new Date().toISOString(),
            isPersisted: false, // Flag to track if this chat exists in DB
        };
        setSessions(prev => [newSession, ...prev]);
        setCurrentSessionId(tempId);

        // Navigate to home if not already there
        if (location.pathname !== '/home') {
            navigation('/home');
        }
    };

    const updateSessionMessages = (sessionId, newMessages) => {
        // Update local state for instant UI, also update title if first user message
        setSessions(prev => prev.map(session => {
            if (session.id === sessionId) {
                let title = session.title;
                if (session.title === 'New Chat' && newMessages.length > 0) {
                    const firstUserMsg = newMessages.find(m => m.type === 'user');
                    if (firstUserMsg) {
                        title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '');
                        // Also update title in the DB (fire-and-forget), but only for persisted chats
                        if (!sessionId.startsWith('temp_')) {
                            axiosJWT.put(`/chat-history/${sessionId}`, { title }).catch(() => { });
                        }
                    }
                }

                return {
                    ...session,
                    messages: newMessages,
                    title: title,
                    timestamp: new Date().toISOString(),
                };
            }
            return session;
        }));

        // Keep loaded messages cache in sync
        setLoadedMessages(prev => ({ ...prev, [sessionId]: newMessages }));
    };

    const persistChatToDatabase = async (tempChatId) => {
        /**
         * Convert a temporary chat to a permanent one in the database.
         * Called on first message sent.
         */
        try {
            const session = sessions.find(s => s.id === tempChatId);
            if (!session) return tempChatId; // Chat not found, shouldn't happen

            // Create the chat in the database
            const res = await axiosJWT.post('/chat-history/', { title: session.title });
            const created = res.data;
            const realChatId = created.id;

            // Update the session with the real database ID
            setSessions(prev => prev.map(s =>
                s.id === tempChatId
                    ? { ...s, id: realChatId, isPersisted: true, timestamp: created.updated_at || new Date().toISOString() }
                    : s
            ));

            // Update current session if it's the one being persisted
            if (currentSessionId === tempChatId) {
                setCurrentSessionId(realChatId);
            }

            // Move loaded messages to the real chat ID
            setLoadedMessages(prev => {
                const messages = prev[tempChatId];
                if (messages) {
                    const updated = { ...prev };
                    delete updated[tempChatId];
                    updated[realChatId] = messages;
                    return updated;
                }
                return prev;
            });

            console.log(`Chat persisted: ${tempChatId} -> ${realChatId}`);
            return realChatId;
        } catch (err) {
            console.error('Failed to persist chat to database:', err);
            return tempChatId; // Return original ID on error, will retry next time
        }
    };

    const deleteSession = async (sessionId, e) => {
        e.stopPropagation();

        try {
            await axiosJWT.delete(`/chat-history/${sessionId}`);
        } catch (err) {
            console.error('Failed to delete chat', err);
        }

        const newSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(newSessions);
        setLoadedMessages(prev => {
            const copy = { ...prev };
            delete copy[sessionId];
            return copy;
        });

        if (sessionId === currentSessionId) {
            if (newSessions.length > 0) {
                setCurrentSessionId(newSessions[0].id);
            } else {
                setCurrentSessionId(null);
            }
        }
    };

    const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0] || null;

    return (
        <div className="flex min-h-screen bg-legal-lightGray dark:bg-[#131416]">
            {/* Sidebar */}
            <Sidebar
                isExpanded={isSidebarExpanded}
                toggleSidebar={toggleSidebar}
                onSettingsClick={handleSettingsClick}
                sessions={sessions}
                currentSessionId={currentSessionId}
                onNewChat={createNewChat}
                onSelectChat={setCurrentSessionId}
                onDeleteChat={deleteSession}
            />

            {/* Main Content Area */}
            <main
                className={`flex-1 transition-all duration-300 ease-in-out ${isSidebarExpanded ? 'ml-64' : 'ml-16'}`}
            >
                <Outlet context={{
                    setToggleSettingsCallback,
                    currentSession,
                    updateSessionMessages,
                    persistChatToDatabase,
                    createNewChat,
                }} />
            </main>
        </div>
    );
};

export default Layout;
