import axios from 'axios';
import { CodeReview, Contributor } from '../types';

// GitHub API base URL
const API_URL = 'https://api.github.com';

// Get GitHub token from environment variables
const GITHUB_TOKEN = process.env.REACT_APP_GITHUB_TOKEN;

// Create an axios instance with common settings
const githubClient = axios.create({
  baseURL: API_URL,
  headers: {
    Accept: 'application/vnd.github+json',
    // Try to get token from environment variables first
    ...(GITHUB_TOKEN && {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      'X-GitHub-Api-Version': `2022-11-28`,
    }),
  },
});

// Add response interceptor to handle GitHub API rate limit errors
githubClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response &&
      error.response.status === 403 &&
      error.response.headers['x-ratelimit-remaining'] === '0'
    ) {
      const resetTime = new Date(
        parseInt(error.response.headers['x-ratelimit-reset']) * 1000,
      );
      const now = new Date();
      const minutesUntilReset = Math.ceil(
        (resetTime.getTime() - now.getTime()) / (1000 * 60),
      );

      error.message =
        `GitHub API rate limit exceeded. Reset in ${minutesUntilReset} minutes. ` +
        `Consider adding a GitHub token for higher limits.`;
    }
    return Promise.reject(error);
  },
);

/**
 * Fetches repository data from GitHub API
 * @param owner Repository owner (user or organization)
 * @param repo Repository name
 */
export const getRepository = async (owner: string, repo: string) => {
  const response = await githubClient.get(`/repos/${owner}/${repo}`);
  return response.data;
};

/**
 * Fetches contributors from a repository
 * @param owner Repository owner
 * @param repo Repository name
 */
export const getContributors = async (
  owner: string,
  repo: string,
): Promise<Contributor[]> => {
  const response = await githubClient.get(
    `/repos/${owner}/${repo}/contributors`,
  );

  // Map the GitHub API response to our Contributor model
  const contributors = await Promise.all(
    response.data.map(async (contributor: any) => {
      // Get additional user details for name and email
      const userDetails = await getUserDetails(contributor.login);

      return {
        id: contributor.id,
        login: contributor.login, // Сохраняем логин для последующих запросов
        avatar: contributor.avatar_url,
        name: userDetails.name || contributor.login,
        email: userDetails.email || 'Нет данных',
        mergeCount: 0, // Изначально ставим 0, потом заполним
        selected: false,
      };
    }),
  );

  // Получаем количество мерджей для всех пользователей
  const mergeCountMap = await getMergedPullRequests(owner, repo);

  // Обновляем каждого контрибьютера с количеством мерджей
  return contributors.map((contributor) => {
    const login = contributor.login;
    const mergeCount = mergeCountMap.get(login) || 0;

    return {
      ...contributor,
      mergeCount,
    };
  });
};

/**
 * Fetches merged pull requests for all contributors within a date range
 * @param owner Repository owner
 * @param repo Repository name
 * @param startDate Start date in ISO format
 * @param endDate End date in ISO format
 */
export const getMergedPullRequests = async (
  owner: string,
  repo: string,
  startDate?: string,
  endDate?: string,
): Promise<Map<string, number>> => {
  // Создаем Map для хранения количества мерджей для каждого пользователя
  const mergeCountMap = new Map<string, number>();

  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = `+merged:${startDate}..${endDate}`;
  }

  // Получаем все смерженные PR для репозитория с фильтром по датам
  const response = await githubClient.get(
    `/search/issues?q=repo:${owner}/${repo}+is:pr+is:merged${dateFilter}&per_page=100`,
  );

  if (response.data && response.data.items) {
    // Для каждого PR получаем информацию о пользователе и увеличиваем счетчик
    for (const pr of response.data.items) {
      const userLogin = pr.user.login;
      mergeCountMap.set(userLogin, (mergeCountMap.get(userLogin) || 0) + 1);
    }
  }

  return mergeCountMap;
};

/**
 * Fetches user details from GitHub API
 * @param username GitHub username
 */
export const getUserDetails = async (username: string) => {
  const response = await githubClient.get(`/users/${username}`);
  return response.data;
};

/**
 * Fetches pull requests by a contributor within a date range
 * @param owner Repository owner
 * @param repo Repository name
 * @param contributor Contributor login
 * @param startDate Start date in ISO format
 * @param endDate End date in ISO format
 */
export const getContributorPullRequests = async (
  owner: string,
  repo: string,
  contributor: string,
  startDate: string,
  endDate: string,
) => {
  // Format the date to GitHub search query format
  const dateFilter = `created:${startDate}..${endDate}`;

  // Fetch merged PRs by the contributor
  const response = await githubClient.get(
    `/search/issues?q=repo:${owner}/${repo}+author:${contributor}+is:pr+is:merged+${dateFilter}`,
  );

  return response.data.items;
};

/**
 * Analyzes code quality for a contributor based on their pull requests
 * This is a mock function that would be replaced with actual AI analysis
 */
export const analyzeCodeQuality = async (
  owner: string,
  repo: string,
  contributorId: number,
  startDate: string,
  endDate: string,
): Promise<CodeReview> => {
  // In a real implementation, this would call an AI service to analyze the code
  // For now, we'll return mock data

  // Generate a random score between 6 and 10
  const randomScore = Math.floor(Math.random() * 5) + 6;

  // Find the contributor by id to get their details
  const contributors = await getContributors(owner, repo);
  const contributor = contributors.find((c) => c.id === contributorId);

  // If no contributor found with this id, return an error
  if (!contributor) {
    throw new Error(`Contributor with id ${contributorId} not found`);
  }

  // Get actual merge count for this contributor
  const mergeCountMap = await getMergedPullRequests(
    owner,
    repo,
    startDate,
    endDate,
  );
  const mergeCount = mergeCountMap.get(contributor.login) || 0;

  return {
    id: contributor.id,
    avatar: contributor.avatar,
    name: contributor.name,
    email: contributor.email,
    mergeCount, // Используем реальное количество мерджей
    status: randomScore >= 8 ? 'Хорошо' : randomScore >= 7 ? 'Средне' : 'Плохо',
    rating: randomScore,
    details: {
      codeStyle: Math.floor(Math.random() * 5) + 6,
      bugFixes: Math.floor(Math.random() * 5) + 6,
      performance: Math.floor(Math.random() * 5) + 6,
      security: Math.floor(Math.random() * 5) + 6,
    },
  };
};

/**
 * Performs code reviews for multiple contributors
 * @param owner Repository owner
 * @param repo Repository name
 * @param contributors List of contributor emails
 * @param startDate Start date in ISO format
 * @param endDate End date in ISO format
 */
export const performCodeReviews = async (
  owner: string,
  repo: string,
  contributors: number[],
  startDate: string,
  endDate: string,
): Promise<CodeReview[]> => {
  const reviews = await Promise.all(
    contributors.map((id) =>
      analyzeCodeQuality(owner, repo, id, startDate, endDate),
    ),
  );

  return reviews;
};

/**
 * Parses a repository URL to extract owner and repo name
 * @param repoUrl Repository URL
 */
export const parseRepositoryUrl = (
  repoUrl: string,
): { owner: string; repo: string } | null => {
  try {
    let url: URL;

    // Handle URLs without protocol
    if (!repoUrl.startsWith('http')) {
      url = new URL(`https://${repoUrl}`);
    } else {
      url = new URL(repoUrl);
    }

    // Extract path components
    const pathParts = url.pathname.split('/').filter(Boolean);

    if (pathParts.length >= 2) {
      return {
        owner: pathParts[0],
        repo: pathParts[1],
      };
    }

    return null;
  } catch (error) {
    console.error('Error parsing repository URL:', error);
    return null;
  }
};
