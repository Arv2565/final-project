import React, { useState, useContext, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { AuthContext } from '../Auth/AuthContext';
import { axiosJWT } from '../Auth/axios';

const Settings = ({ onClose }) => {
    const [activeTab, setActiveTab] = useState('general');
    const { theme, toggleTheme } = useTheme();
    const { user, login } = useContext(AuthContext);

    // Account form state
    const [fullName, setFullName] = useState('');
    const [claudeName, setClaudeName] = useState('');
    const [workFunction, setWorkFunction] = useState('');
    const [preferences, setPreferences] = useState('');
    
    // UI state
    const [isSaving, setIsSaving] = useState(false);
    const [notification, setNotification] = useState(null);

    // Load user data on mount
    useEffect(() => {
        if (user) {
            setFullName(user.name || '');
            setClaudeName(user.name || '');
            // Parse bio field to extract work function (first line) and preferences (rest)
            const bioLines = (user.bio || '').split('\n');
            if (bioLines[0]) {
                setWorkFunction(bioLines[0]);
            }
            if (bioLines[1]) {
                setPreferences(bioLines.slice(1).join('\n'));
            }
        }
    }, [user]);

    // Get first 2 letters of name for avatar
    const getInitials = (name) => {
        if (!name) return 'U';
        return name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    };

    // Validate form
    const validateForm = () => {
        if (!fullName.trim()) {
            showNotification('Full name is required', 'error');
            return false;
        }
        if (fullName.trim().length < 2) {
            showNotification('Full name must be at least 2 characters', 'error');
            return false;
        }
        return true;
    };

    // Show notification
    const showNotification = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    // Handle save changes
    const handleSaveChanges = async () => {
        if (!validateForm()) return;

        setIsSaving(true);
        try {
            // Combine work function and preferences into bio field
            const bioContent = [workFunction, preferences].filter(Boolean).join('\n');

            const updateData = {
                name: fullName,
                bio: bioContent,
                personal_preferences: preferences,
            };

            const response = await axiosJWT.put('/user/profile', updateData);
            
            if (response.data) {
                // Refetch user data to update context
                try {
                    const userRes = await axiosJWT.get('/user');
                    if (userRes.data && !userRes.data.errorCode) {
                        const updatedUserData = {
                            id: userRes.data.id,
                            username: userRes.data.username,
                            name: userRes.data.name,
                            email: userRes.data.email,
                            profilePicture: userRes.data.profilePicture,
                            bio: userRes.data.bio,
                            personal_preferences: userRes.data.personal_preferences,
                        };
                        // Update context with new user data
                        login(updatedUserData);
                    }
                } catch (refreshError) {
                    console.warn('Failed to refresh user data:', refreshError);
                }

                showNotification('Changes saved successfully!', 'success');
            }
        } catch (error) {
            console.error('Failed to save changes:', error);
            showNotification(
                error.response?.data?.detail || 'Failed to save changes',
                'error'
            );
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="w-full h-full flex bg-legal-lightGray dark:bg-[#131416]">
            {/* Toast Notification */}
            {notification && (
                <div className={`fixed top-4 right-4 px-4 py-3 rounded-lg text-white shadow-lg z-50 transition-all duration-300 ${
                    notification.type === 'success'
                        ? 'bg-green-500'
                        : 'bg-red-500'
                }`}>
                    {notification.message}
                </div>
            )}
            {/* Left Sidebar */}
            <div className="w-48 border-r border-legal-borders dark:border-white/10 bg-legal-lightGray dark:bg-[#131416] p-6">
                <h1 className="text-2xl font-bold text-legal-darkNavy dark:text-white mb-8">Settings</h1>
                <div className="space-y-2">
                    <button
                        onClick={() => setActiveTab('general')}
                        className={`w-full text-left px-4 py-2.5 rounded-lg transition-colors ${
                            activeTab === 'general'
                                ? 'bg-legal-navy text-white dark:bg-white/10 dark:text-white'
                                : 'text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white hover:bg-blue-50 dark:hover:bg-white/5'
                        }`}
                    >
                        General
                    </button>
                    <button
                        onClick={() => setActiveTab('account')}
                        className={`w-full text-left px-4 py-2.5 rounded-lg transition-colors ${
                            activeTab === 'account'
                                ? 'bg-legal-navy text-white dark:bg-white/10 dark:text-white'
                                : 'text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white hover:bg-blue-50 dark:hover:bg-white/5'
                        }`}
                    >
                        Account
                    </button>
                </div>
            </div>

            {/* Right Content Area */}
            <div className="flex-1 p-8 overflow-y-auto bg-legal-lightGray dark:bg-[#0a0b0d]">
                {/* Close Button */}
                <div className="mb-8 flex justify-end">
                    <button
                        onClick={onClose}
                        className="text-legal-gray dark:text-gray-400 hover:text-legal-darkNavy dark:hover:text-white transition-colors p-2 rounded-lg hover:bg-legal-lightGray dark:hover:bg-white/10"
                    >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>

                {/* General Tab */}
                {activeTab === 'general' && (
                    <div className="space-y-8 max-w-2xl">
                        <div>
                            <h2 className="text-xl font-semibold text-legal-darkNavy dark:text-white mb-6">General Settings</h2>
                        </div>

                        {/* Appearance Section */}
                        <div>
                            <h3 className="text-lg font-semibold text-legal-darkNavy dark:text-white mb-4">Appearance</h3>
                            <div className="space-y-4">
                                <div>
                                    <p className="text-legal-gray dark:text-gray-300 text-sm mb-3">Color mode</p>
                                    <div className="flex gap-4">
                                        {[
                                            { name: 'Light', value: 'light' },
                                            { name: 'Auto', value: 'auto' },
                                            { name: 'Dark', value: 'dark' }
                                        ].map(({ name, value }) => (
                                            <button
                                                key={value}
                                                onClick={() => toggleTheme(value)}
                                                className={`flex flex-col items-center gap-2 p-3 rounded-lg border transition-all ${
                                                    theme === value
                                                        ? 'border-legal-gold bg-yellow-50 dark:bg-blue-950/30'
                                                        : 'border-legal-borders dark:border-white/10 hover:border-legal-navy dark:hover:border-white/30'
                                                } group`}
                                            >
                                                <div className="w-24 h-16 rounded-md bg-gradient-to-b from-legal-lightGray to-legal-lightGray group-hover:from-legal-borders group-hover:to-legal-borders transition-colors">
                                                    {value === 'dark' && (
                                                        <div className="w-full h-full bg-legal-darkNavy rounded-md"></div>
                                                    )}
                                                </div>
                                                <span className={`text-sm font-medium ${
                                                    theme === value
                                                        ? 'text-legal-gold dark:text-legal-lightGold'
                                                        : 'text-legal-gray dark:text-gray-300 group-hover:text-legal-darkNavy dark:group-hover:text-white'
                                                }`}>
                                                    {name}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Notifications Section */}
                        <div>
                            <h3 className="text-lg font-semibold text-legal-darkNavy dark:text-white mb-4">Notifications</h3>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-3 rounded-lg bg-legal-lightGray dark:bg-white/5 border border-legal-borders dark:border-white/10">
                                    <div>
                                        <p className="text-legal-darkNavy dark:text-gray-300 font-medium">Response completions</p>
                                        <p className="text-legal-gray dark:text-gray-400 text-sm">Get notified when Dike has finished a response.</p>
                                    </div>
                                    <div className="w-12 h-7 bg-legal-navy rounded-full cursor-pointer relative flex items-center justify-end pr-1">
                                        <div className="w-5 h-5 bg-white rounded-full"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Account Tab */}
                {activeTab === 'account' && (
                    <div className="space-y-8 max-w-2xl">
                        <div>
                            <h2 className="text-xl font-semibold text-legal-darkNavy dark:text-white mb-6">Account Settings</h2>
                            <div className="space-y-4">
                                {/* Full name */}
                                <div>
                                    <label className="text-legal-darkNavy dark:text-gray-400 text-sm block mb-2">Full name</label>
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-legal-navy to-legal-gold flex items-center justify-center text-white text-sm font-bold">
                                            {getInitials(fullName)}
                                        </div>
                                        <input
                                            type="text"
                                            value={fullName}
                                            onChange={(e) => setFullName(e.target.value)}
                                            className="flex-1 bg-legal-lightGray dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 text-legal-darkNavy dark:text-gray-300 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-legal-navy dark:focus:border-white/30"
                                        />
                                    </div>
                                </div>

                                {/* Claude Name */}
                                <div>
                                    <label className="text-legal-darkNavy dark:text-gray-400 text-sm block mb-2">What should Claude call you?</label>
                                    <input
                                        type="text"
                                        value={claudeName}
                                        onChange={(e) => setClaudeName(e.target.value)}
                                        className="w-full bg-legal-lightGray dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 text-legal-darkNavy dark:text-gray-300 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-legal-navy dark:focus:border-white/30"
                                    />
                                </div>

                                {/* Work Function */}
                                <div>
                                    <label className="text-legal-darkNavy dark:text-gray-400 text-sm block mb-2">What best describes your work?</label>
                                    <select 
                                        value={workFunction}
                                        onChange={(e) => setWorkFunction(e.target.value)}
                                        className="w-full bg-legal-lightGray dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 text-legal-darkNavy dark:text-gray-300 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-legal-navy dark:focus:border-white/30"
                                    >
                                        <option value="">Select your work function</option>
                                        <option value="Attorney">Attorney</option>
                                        <option value="Paralegal">Paralegal</option>
                                        <option value="Legal Consultant">Legal Consultant</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>

                                {/* Preferences */}
                                <div>
                                    <label className="text-legal-darkNavy dark:text-gray-400 text-sm block mb-2">What personal preferences should Dike consider in responses?</label>
                                    <p className="text-legal-gray dark:text-gray-500 text-xs mb-2">Your preferences will apply to all conversations.</p>
                                    <textarea
                                        value={preferences}
                                        onChange={(e) => setPreferences(e.target.value)}
                                        placeholder="e.g. when learning new concepts, I find analogies particularly helpful"
                                        className="w-full bg-legal-lightGray dark:bg-[#1e1f23] border border-legal-borders dark:border-white/10 text-legal-darkNavy dark:text-gray-300 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-legal-navy dark:focus:border-white/30 resize-none h-24"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Save Button */}
                        <div className="pt-4">
                            <button 
                                onClick={handleSaveChanges}
                                disabled={isSaving}
                                className="px-6 py-2 bg-legal-navy hover:bg-legal-darkNavy disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
                            >
                                {isSaving ? 'Saving...' : 'Save changes'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Settings;
