import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import axios from 'axios';

export default function Signup() {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        try {
            const formData = { name, username, email, phone, password };
            await axios.post('http://localhost:8000/api/auth/signup', formData);
            // Redirect to login on success
            navigate('/');
        } catch (err) {
            setError(err.response?.data?.detail || 'An error occurred during signup');
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 py-12">
            <div className="bg-white p-8 rounded-lg shadow-md w-96 max-h-[90vh] overflow-y-auto mt-4 mb-4">
                <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Sign Up</h2>
                <form className="space-y-4" onSubmit={handleSubmit}>
                    {error && <div className="text-red-500 text-sm text-center">{error}</div>}
                    <div>
                        <label className="block text-gray-700 mb-2">Name</label>
                        <input
                            type="text"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="Your Name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Username</label>
                        <input
                            type="text"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="Your Username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Email</label>
                        <input
                            type="email"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="user@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Phone</label>
                        <input
                            type="tel"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="Your Phone Number"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Password</label>
                        <input
                            type="password"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="********"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Confirm Password</label>
                        <input
                            type="password"
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            placeholder="********"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition duration-300">
                        Create Account
                    </button>
                </form>
                <p className="mt-4 text-center text-gray-600">
                    Already have an account? <Link to="/" className="text-green-500 hover:underline">Login</Link>
                </p>
                <div className="mt-4 text-center">
                    <Link to="/" className="text-gray-500 hover:text-gray-700 text-sm">Back to Home</Link>
                </div>
            </div>
        </div>
    );
}
