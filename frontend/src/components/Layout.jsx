import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const Layout = () => {
    const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);
    const [toggleSettingsCallback, setToggleSettingsCallback] = useState(null);

    const toggleSidebar = () => {
        setIsSidebarExpanded(!isSidebarExpanded);
    };

    const handleSettingsClick = () => {
        if (toggleSettingsCallback) {
            toggleSettingsCallback();
        }
    };

    return (
        <div className="flex min-h-screen bg-legal-lightGray dark:bg-[#131416]">
            {/* Sidebar */}
            <Sidebar isExpanded={isSidebarExpanded} toggleSidebar={toggleSidebar} onSettingsClick={handleSettingsClick} />

            {/* Main Content Area */}
            <main
                className={`flex-1 transition-all duration-300 ease-in-out ${isSidebarExpanded ? 'ml-64' : 'ml-16'}`}
            >
                <Outlet context={{ setToggleSettingsCallback }} />
            </main>
        </div>
    );
};

export default Layout;
