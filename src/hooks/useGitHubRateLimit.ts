import { useState, useEffect } from 'react';

/**
 * Hook to manage GitHub API rate limit status
 * This will check if a rate limit error has been encountered
 * and manage the token from session storage
 */
export function useGitHubRateLimit() {
  const [isRateLimited, setIsRateLimited] = useState<boolean>(false);
  
  useEffect(() => {
    // Listen for custom events that could be dispatched when rate limit is hit
    const handleRateLimitExceeded = () => {
      setIsRateLimited(true);
    };

    window.addEventListener('github-rate-limit-exceeded', handleRateLimitExceeded);
    
    // Check if there was a rate limit error stored
    const hasRateLimitError = sessionStorage.getItem('github-rate-limit-error') === 'true';
    if (hasRateLimitError) {
      setIsRateLimited(true);
    }
    
    return () => {
      window.removeEventListener('github-rate-limit-exceeded', handleRateLimitExceeded);
    };
  }, []);
  
  return { isRateLimited, setIsRateLimited };
}

export default useGitHubRateLimit;
