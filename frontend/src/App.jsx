import { Routes, Route, Navigate } from "react-router-dom";
import Signup from './pages/Signup';
import Login from './pages/Login';
import Home from './pages/Home';
import { AuthProvider } from './Auth/AuthContext';
import Profile from "./pages/Profile";
import Exchanges from "./pages/Exchanges";
import Layout from "./components/Layout";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        <Route element={<Layout />}>
          <Route path="/home" element={<Home />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/exchanges" element={<Exchanges />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
