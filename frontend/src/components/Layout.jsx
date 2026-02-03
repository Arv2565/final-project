import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

const Layout = () => {
    const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);
    const [toggleSettingsCallback, setToggleSettingsCallback] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const navigation = useNavigate();
    const location = useLocation();

    // Load sessions from local storage on mount
    useEffect(() => {
        const savedSessions = localStorage.getItem('chatSessions');
        if (savedSessions) {
            try {
                const parsedSessions = JSON.parse(savedSessions);
                if (Array.isArray(parsedSessions) && parsedSessions.length > 0) {
                    setSessions(parsedSessions);

                    // Restore last active session if exists, otherwise first
                    const lastActive = localStorage.getItem('lastActiveSessionId');
                    // loose comparison for string/number compatibility
                    const sessionExists = parsedSessions.find(s => String(s.id) === String(lastActive));
                    setCurrentSessionId(sessionExists ? sessionExists.id : parsedSessions[0].id);
                } else {
                    createNewChat();
                }
            } catch (e) {
                console.error("Failed to parse sessions", e);
                createNewChat();
            }
        } else {
            createNewChat();
        }
    }, []);

    // Save sessions to local storage whenever they change
    useEffect(() => {
        if (sessions.length > 0) {
            localStorage.setItem('chatSessions', JSON.stringify(sessions));
        }
    }, [sessions]);

    // Save active session ID
    useEffect(() => {
        if (currentSessionId) {
            localStorage.setItem('lastActiveSessionId', currentSessionId);
        }
    }, [currentSessionId]);

    const toggleSidebar = () => {
        setIsSidebarExpanded(!isSidebarExpanded);
    };

    const handleSettingsClick = () => {
        if (toggleSettingsCallback) {
            toggleSettingsCallback();
        }
    };

    const createNewChat = () => {
        const newSession = {
            id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            title: 'New Chat',
            messages: [],
            timestamp: new Date().toISOString()
        };
        setSessions(prev => [newSession, ...prev]);
        setCurrentSessionId(newSession.id);

        // Navigate to home if not already there
        if (location.pathname !== '/') {
            navigation('/');
        }
    };

    const updateSessionMessages = (sessionId, newMessages) => {
        setSessions(prev => prev.map(session => {
            if (session.id === sessionId) {
                // Generate a title based on the first user message if it's "New Chat" and has messages
                let title = session.title;
                if (session.title === 'New Chat' && newMessages.length > 0) {
                    const firstUserMsg = newMessages.find(m => m.type === 'user');
                    if (firstUserMsg) {
                        title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '');
                    }
                }

                return {
                    ...session,
                    messages: newMessages,
                    title: title,
                    timestamp: new Date().toISOString()
                };
            }
            return session;
        }));
    };

    const deleteSession = (sessionId, e) => {
        e.stopPropagation(); // Prevent triggering selectSession
        const newSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(newSessions);

        // If we deleted the current session
        if (sessionId === currentSessionId) {
            if (newSessions.length > 0) {
                setCurrentSessionId(newSessions[0].id);
            } else {
                // If no sessions left, create a new one (which will trigger standard init)
                // But simply clearing and calling createNewChat might be safer
                createNewChat();
            }
        }

        // If we deleted the last session, update local storage immediately to avoid sync issues
        if (newSessions.length === 0) {
            localStorage.removeItem('chatSessions');
        }
    };

    // Ensure session IDs are comparable (strings vs numbers issue fix from previous Date.now())
    const currentSession = sessions.find(s => String(s.id) === String(currentSessionId)) || sessions[0];

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
                    updateSessionMessages
                }} />
            </main>
        </div>
    );
};

export default Layout;
