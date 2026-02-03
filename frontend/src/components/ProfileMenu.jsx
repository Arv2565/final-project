import React, { useState, useRef, useEffect } from 'react';

const ProfileMenu = ({ isExpanded, onSettingsClick }) => {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef(null);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    const menuItems = [
        { icon: 'settings', label: 'Settings', id: 'settings' },
        { icon: 'language', label: 'Language', id: 'language' },
        { icon: 'help', label: 'Get help', id: 'help' },
        { icon: 'info', label: 'Learn more', id: 'learn' },
        { icon: 'logout', label: 'Log out', id: 'logout' },
    ];

    const handleMenuItemClick = (id) => {
        if (id === 'settings' && onSettingsClick) {
            onSettingsClick();
        } else {
            console.log(`Clicked: ${id}`);
        }
        setIsOpen(false);
    };

    return (
        <div ref={menuRef} className="relative">
            {/* Profile Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-3 w-full ${isExpanded ? '' : 'justify-center'} px-3 py-2 rounded-lg hover:bg-legal-lightGray dark:hover:bg-white/10 transition-colors`}
            >
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-legal-navy to-legal-gold flex items-center justify-center text-white text-xs font-bold shrink-0">
                    JD
                </div>
                <div className={`flex flex-col overflow-hidden transition-all duration-300 ${isExpanded ? 'opacity-100 w-auto' : 'opacity-0 w-0'}`}>
                    <span className="text-sm text-legal-darkNavy dark:text-white font-medium truncate">John Doe</span>
                </div>
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className={`absolute bottom-full mb-2 bg-white dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 rounded-lg shadow-xl z-50 ${isExpanded ? 'left-0 right-0 w-56' : 'left-1/2 transform -translate-x-1/2 w-56'}`}>
                    {/* Email Header */}
                    <div className="px-4 py-3 border-b border-legal-borders dark:border-white/5">
                        <p className="text-sm text-legal-gray dark:text-gray-400">johndoe@gmail.com</p>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                        {menuItems.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => handleMenuItemClick(item.id)}
                                className={`w-full px-4 py-2.5 flex items-center gap-3 text-legal-gray dark:text-gray-300 transition-colors text-sm ${
                                    item.id === 'logout'
                                        ? 'hover:bg-red-100 dark:hover:bg-red-600 hover:text-red-700 dark:hover:text-white'
                                        : 'hover:bg-legal-navy/10 dark:hover:bg-white/10 hover:text-legal-darkNavy dark:hover:text-white'
                                }`}
                            >
                                {/* Icon rendering based on item type */}
                                {item.id === 'settings' && (
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="3"></circle>
                                        <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m2.12 2.12l4.24 4.24M1 12h6m6 0h6m-17.78 7.78l4.24-4.24m2.12-2.12l4.24-4.24"></path>
                                    </svg>
                                )}
                                {item.id === 'language' && (
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                                        <path d="M2 12h20"></path>
                                    </svg>
                                )}
                                {item.id === 'help' && (
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <path d="M12 16v-4"></path>
                                        <path d="M12 8h.01"></path>
                                    </svg>
                                )}
                                {item.id === 'learn' && (
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="1"></circle>
                                        <path d="M12 17v4"></path>
                                        <path d="M12 3v4"></path>
                                        <path d="M20.485 6.515l2.828 2.828"></path>
                                        <path d="M3.343 20.657l2.828 2.828"></path>
                                        <path d="M3.515 3.515l2.828 2.828"></path>
                                        <path d="M20.657 20.657l2.828 2.828"></path>
                                        <path d="M3 12h4"></path>
                                        <path d="M17 12h4"></path>
                                    </svg>
                                )}
                                {item.id === 'logout' && (
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                        <polyline points="16 17 21 12 16 7"></polyline>
                                        <line x1="21" y1="12" x2="9" y2="12"></line>
                                    </svg>
                                )}
                                <span>{item.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProfileMenu;
