import { Link } from 'react-router-dom';

const SignIn = () => {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
            <div className="bg-white p-8 rounded-lg shadow-md w-96">
                <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Sign In</h2>
                <form className="space-y-4">
                    <div>
                        <label className="block text-gray-700 mb-2">Name</label>
                        <input type="text" className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="Your Name" />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Email</label>
                        <input type="email" className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="user@example.com" />
                    </div>
                    <div>
                        <label className="block text-gray-700 mb-2">Password</label>
                        <input type="password" className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="********" />
                    </div>
                    <button type="button" className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition duration-300">
                        Create Account
                    </button>
                </form>
                <p className="mt-4 text-center text-gray-600">
                    Already have an account? <Link to="/login" className="text-green-500 hover:underline">Login</Link>
                </p>
                <div className="mt-4 text-center">
                    <Link to="/" className="text-gray-500 hover:text-gray-700 text-sm">Back to Home</Link>
                </div>
            </div>
        </div>
    );
};

export default SignIn;
