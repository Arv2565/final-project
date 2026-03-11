import React, { useState, useEffect, useContext } from 'react';
import { useOutletContext } from 'react-router-dom';
import ChatInterface from '../components/ChatInterface';
import DraftBuilder from '../components/DraftBuilder';
import Settings from '../components/Settings';
import { AuthContext } from '../Auth/AuthContext';

const Home = () => {
    const [isDraftOpen, setIsDraftOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [draftContent, setDraftContent] = useState('');
    const {
        setToggleSettingsCallback,
        currentSession,
        updateSessionMessages,
        persistChatToDatabase,
        persistDraftContent,
        createNewChat,
        setCloseDraftCallback
    } = useOutletContext();
    const { user } = useContext(AuthContext);
    const userId = user?.id || null;
    const userDisplayName = (user?.name || user?.username || '').trim();

    const toggleDraft = (content = '') => {
        // Only treat a string as content; React events can accidentally be passed here.
        if (typeof content === 'string' && content.trim() !== '') {
            setDraftContent(content);
        }
        setIsDraftOpen(true);
    };

    const closeDraft = () => {
        setIsDraftOpen(false);
    };

    const handleSwitchToPreview = async (latestContent) => {
        const sessionId = currentSession?.id;
        if (!sessionId || !persistDraftContent) return;
        await persistDraftContent(sessionId, latestContent || '');
    };

    const toggleSettings = () => {
        setIsSettingsOpen(!isSettingsOpen);
    };

    useEffect(() => {
        setToggleSettingsCallback(() => toggleSettings);
    }, [setToggleSettingsCallback]);

    useEffect(() => {
        if (setCloseDraftCallback) {
            setCloseDraftCallback(() => closeDraft);
        }
    }, [setCloseDraftCallback]);

    // Show Settings if open
    if (isSettingsOpen) {
        return (
            <div className="bg-legal-lightGray dark:bg-[#131416] text-legal-darkNavy dark:text-white font-sans h-[calc(100vh-2rem)] flex overflow-hidden p-4 gap-4 box-border">
                <Settings onClose={toggleSettings} />
            </div>
        );
    }

    return (
        <div className="bg-legal-lightGray dark:bg-[#131416] text-legal-darkNavy dark:text-white font-sans h-[calc(100vh-2rem)] flex overflow-hidden p-4 gap-4 box-border">
            <div className={`h-full grid gap-4 overflow-hidden ${isDraftOpen ? 'grid-cols-2' : 'grid-cols-1'} w-full`}>
                <div className="h-full min-w-0 overflow-hidden">
                    <ChatInterface
                        isDraftOpen={isDraftOpen}
                        toggleDraft={toggleDraft}
                        toggleSettings={toggleSettings}
                        currentSession={currentSession}
                        onUpdateMessages={(msgs) => updateSessionMessages(currentSession?.id, msgs)}
                        persistChatToDatabase={persistChatToDatabase}
                        createNewChat={createNewChat}
                        userId={userId}
                        userName={userDisplayName}
                    />
                </div>
                {isDraftOpen && (
                    <div className="h-full min-w-0 overflow-hidden">
                        <DraftBuilder
                            onClose={closeDraft}
                            content={draftContent}
                            onContentChange={setDraftContent}
                            onSwitchToPreview={handleSwitchToPreview}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

export default Home;

