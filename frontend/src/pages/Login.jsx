import { Link, useNavigate } from 'react-router-dom';
import { useState, useContext } from 'react';
import axios from 'axios';
import { AuthContext } from '../Auth/AuthContext';
import { useTheme } from '../context/ThemeContext';
import ThemeToggle from '../components/ThemeToggle';
import { Mail, Lock, Loader2 } from 'lucide-react';

const Login = () => {
    const navigate = useNavigate();
    const { authorize } = useContext(AuthContext);
    const { theme } = useTheme();

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const res = await axios.post('http://localhost:8000/api/auth/login', { username, password });

            if (res.data.errorCode) {
                setError(res.data.message);
                setIsLoading(false);
                return;
            }

            document.cookie = `auth=${res.data.accessToken}; path=/; secure; samesite=strict`;
            document.cookie = `ref=${res.data.refreshToken}; path=/; secure; samesite=strict`;

            await authorize();
            navigate('/home');
        } catch (err) {
            setError(err.response?.data?.detail || 'An error occurred during login');
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-white dark:bg-[#131416] transition-colors duration-300 flex items-center justify-center p-4 relative overflow-hidden">
            {/* Decorative elements */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 dark:bg-blue-900/20 rounded-full blur-3xl opacity-0 dark:opacity-100 transition-opacity duration-300"></div>
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/10 dark:bg-purple-900/20 rounded-full blur-3xl opacity-0 dark:opacity-100 transition-opacity duration-300"></div>
            </div>

            {/* Theme Toggle */}
            <div className="absolute top-8 right-8 z-50">
                <ThemeToggle />
            </div>

            {/* Main Content */}
            <div className="w-full max-w-md relative z-10">
                {/* Header */}
                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight">
                        Welcome back
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 text-base">
                        Sign in to your account to continue
                    </p>
                </div>

                {/* Form Container */}
                <div className="bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm dark:shadow-2xl p-8 space-y-6 transition-all duration-300">
                    {/* Error Message */}
                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg">
                            <p className="text-red-700 dark:text-red-400 text-sm font-medium">{error}</p>
                        </div>
                    )}

                    {/* Form */}
                    <form className="space-y-5" onSubmit={handleSubmit}>
                        {/* Username Input */}
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-900 dark:text-white">
                                Username or Email
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-400 dark:text-gray-500" />
                                <input
                                    type="text"
                                    className="w-full pl-12 pr-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200"
                                    placeholder="you@example.com"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        {/* Password Input */}
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-900 dark:text-white">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-3.5 w-5 h-5 text-gray-400 dark:text-gray-500" />
                                <input
                                    type="password"
                                    className="w-full pl-12 pr-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-sm hover:shadow-md"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                'Sign in'
                            )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-2 bg-white dark:bg-[#1e1e1e] text-gray-600 dark:text-gray-400">
                                New to our platform?
                            </span>
                        </div>
                    </div>

                    {/* Sign Up Link */}
                    <p className="text-center text-gray-600 dark:text-gray-400">
                        Don't have an account?{' '}
                        <Link
                            to="/signup"
                            className="text-blue-600 dark:text-blue-400 font-semibold hover:underline transition-colors duration-200"
                        >
                            Create one
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
