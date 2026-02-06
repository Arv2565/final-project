import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import ChatInterface from '../components/ChatInterface';
import DraftBuilder from '../components/DraftBuilder';
import Settings from '../components/Settings';

const Home = () => {
    const [isDraftOpen, setIsDraftOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [draftContent, setDraftContent] = useState('');
    const {
        setToggleSettingsCallback,
        currentSession,
        updateSessionMessages
    } = useOutletContext();

    const toggleDraft = (content = '') => {
        if (content) {
            setDraftContent(content);
            setIsDraftOpen(true);
        } else {
            setIsDraftOpen(!isDraftOpen);
        }
    };

    const toggleSettings = () => {
        setIsSettingsOpen(!isSettingsOpen);
    };

    useEffect(() => {
        setToggleSettingsCallback(() => toggleSettings);
    }, [setToggleSettingsCallback]);

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

            {/* Left Panel - Chat Interface */}
            {/* If Draft is open, Chat takes less width, otherwise full width */}
            {/* Main Layout Grid */}
            <div className={`h-full grid gap-4 overflow-hidden ${isDraftOpen ? 'grid-cols-2' : 'grid-cols-1'} w-full`}>

                {/* Left Panel - Chat Interface */}
                <div className="h-full min-w-0 overflow-hidden">
                    <ChatInterface
                        key={currentSession?.id}
                        isDraftOpen={isDraftOpen}
                        toggleDraft={toggleDraft}
                        toggleSettings={toggleSettings}
                        currentSession={currentSession}
                        onUpdateMessages={(msgs) => updateSessionMessages(currentSession?.id, msgs)}
                    />
                </div>

                {/* Right Panel - Draft Builder */}
                {isDraftOpen && (
                    <div className="h-full min-w-0 overflow-hidden">
                        <DraftBuilder onClose={toggleDraft} content={draftContent} />
                    </div>
                )}
            </div>

        </div>
    );
};

export default Home;

