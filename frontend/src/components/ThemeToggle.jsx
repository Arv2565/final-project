import { useTheme } from '../context/ThemeContext';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={() => toggleTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2.5 rounded-full transition-all duration-300 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? (
        <Sun size={20} className="text-yellow-400" />
      ) : (
        <Moon size={20} className="text-gray-600" />
      )}
    </button>
  );
}
