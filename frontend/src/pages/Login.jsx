import { Link, useNavigate } from 'react-router-dom';
import { useState, useContext } from 'react';
import axios from 'axios';
import { AuthContext } from '../Auth/AuthContext';

const Login = () => {
    const navigate = useNavigate();
    const { authorize } = useContext(AuthContext);

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const res = await axios.post('http://localhost:8000/api/auth/login', { username, password });

            // Expected backend format: { accessToken, refreshToken } OR { errorCode, message }
            if (res.data.errorCode) {
                setError(res.data.message);
                return;
            }

            // Set cookies
            document.cookie = `auth=${res.data.accessToken}; path=/; secure; samesite=strict`;
            document.cookie = `ref=${res.data.refreshToken}; path=/; secure; samesite=strict`;

            await authorize(); // Fetch full user data from /user endpoint
            navigate('/home');
        } catch (err) {
            setError(err.response?.data?.detail || 'An error occurred during login');
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
            <div className="bg-white p-8 rounded-lg shadow-md w-96">
                <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Login</h2>
                <form className="space-y-4" onSubmit={handleSubmit}>
                    {error && <div className="text-red-500 text-sm text-center">{error}</div>}
                    <div>
                        <label className="block text-gray-700 mb-2">Username</label>
                        <input
                            type="text"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Your Username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Password</label>
                        <input
                            type="password"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="********"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition duration-300">
                        Log In
                    </button>
                </form>
                <p className="mt-4 text-center text-gray-600">
                    Don't have an account? <Link to="/signup" className="text-blue-500 hover:underline">Sign Up</Link>
                </p>
                <div className="mt-4 text-center">
                    <Link to="/" className="text-gray-500 hover:text-gray-700 text-sm">Back to Home</Link>
                </div>
            </div>
        </div>
    );
};

export default Login;
