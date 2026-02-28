import { createContext, useState, useEffect } from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import { axiosJWT } from "./axios";
import { getCookie } from "../utils";

// Create the AuthContext
export const AuthContext = createContext();

// AuthProvider component to wrap your application
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null); // Complete user object
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();
    const location = useLocation();

    const authorize = async () => {
        setIsLoading(true);
        try {
            const res = await axiosJWT.get('/user');
            if (res.data.errorCode != null) {
                // User not authenticated
                setUser(null);
                setIsLoggedIn(false);
                if (location.pathname !== '/' && location.pathname !== '/login' && location.pathname !== '/signup') {
                    navigate('/login', { replace: true });
                }
            } else {
                // User authenticated
                const userData = {
                    id: res.data.id,
                    username: res.data.username,
                    name: res.data.name,
                    email: res.data.email,
                    profilePicture: res.data.profilePicture,
                    // Add any other user fields from the response
                };
                setUser(userData);
                setIsLoggedIn(true);
            }
        } catch (err) {
            console.error('Authorization error:', err);
            setUser(null);
            setIsLoggedIn(false);
            // Only redirect if not already on public pages
            if (location.pathname !== '/' && location.pathname !== '/login' && location.pathname !== '/signup') {
                navigate('/login', { replace: true });
            }
        } finally {
            setIsLoading(false);
        }
    };

    const logout = () => {
        // Clear cookies
        document.cookie = 'auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        document.cookie = 'ref=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        
        // Clear user state
        setUser(null);
        setIsLoggedIn(false);
        
        // Redirect to login page
        navigate('/login', { replace: true });
    };

    const login = (userData) => {
        setUser(userData);
        setIsLoggedIn(true);
    };

    // Auto-fetch user on mount if auth cookie exists
    useEffect(() => {
        const token = getCookie('auth');
        if (token) {
            authorize();
        } else {
            setIsLoading(false);
        }
    }, []);

    const context = { 
        user, 
        isLoggedIn, 
        isLoading, 
        authorize, 
        logout, 
        login,
        // Backward compatibility
        id: user?.id,
        name: user?.name
    };

    return (
        <AuthContext.Provider value={context}>
        {children}
        </AuthContext.Provider>
    );
};

export default AuthContext;
