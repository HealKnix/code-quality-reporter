import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

interface RateLimitAlertProps {
  isVisible: boolean;
}

export const RateLimitAlert: React.FC<RateLimitAlertProps> = ({ isVisible }) => {
  const [token, setToken] = useState('');
  const [showTokenInput, setShowTokenInput] = useState(false);

  if (!isVisible) return null;

  const handleSaveToken = () => {
    // In a real app, you would store this in localStorage or a secure storage
    // For demo purposes, we can use sessionStorage
    if (token) {
      sessionStorage.setItem('githubToken', token);
      alert('Token saved! Please refresh the page for it to take effect.');
    }
  };

  return (
    <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <AlertCircle className="h-5 w-5 text-red-400" />
        </div>
        <div className="ml-3">
          <p className="text-sm text-red-700">
            <strong>GitHub API rate limit exceeded.</strong> You've reached the limit for unauthenticated requests.
          </p>
          <div className="mt-2">
            {!showTokenInput ? (
              <button 
                className="text-sm font-medium text-red-700 hover:text-red-600"
                onClick={() => setShowTokenInput(true)}
              >
                Add a GitHub token to increase your rate limit
              </button>
            ) : (
              <div className="mt-2 space-y-2">
                <p className="text-xs text-gray-600">
                  Create a token at <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="underline">github.com/settings/tokens</a> (no specific permissions needed for public repos)
                </p>
                <div className="flex space-x-2">
                  <input 
                    type="text" 
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Paste your GitHub token" 
                    className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                  />
                  <button
                    onClick={handleSaveToken}
                    className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RateLimitAlert;
