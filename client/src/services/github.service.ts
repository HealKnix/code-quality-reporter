import axios from 'axios';
import { CodeReview, Contributor } from '@/types';

// GitHub API base URL
const API_URL = process.env.REACT_APP_API_BASE_URL;

// Create an axios instance with common settings
const githubClient = axios.create({
  baseURL: API_URL,
  headers: {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  },
});

// Добавляем интерцептор запросов для динамического обновления токена
githubClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('githubToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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
  const { data } = await githubClient.get(
    `https://api.github.com/repos/${owner}/${repo}`,
  );

  return data;
};

/**
 * Fetches contributors from a repository
 * @param owner Repository owner
 * @param repo Repository name
 * @param startDate Optional start date for filtering merge count
 * @param endDate Optional end date for filtering merge count
 */
export const getContributors = async (
  owner: string,
  repo: string,
  startDate?: string,
  endDate?: string,
): Promise<Contributor[]> => {
  const { data } = await githubClient.get<Contributor[]>(
    `https://api.github.com/repos/${owner}/${repo}/contributors`,
  );

  // Получаем количество мерджей для всех пользователей
  const mergeCountMap = await getMergedPullRequests(
    owner,
    repo,
    startDate,
    endDate,
  );

  const contributors = data.map((contributor) => {
    return {
      ...contributor,
      email: contributor.email || 'Нет данных',
      name: contributor.name || contributor.login,
      mergeCount: 0, // Изначально ставим 0, потом заполним
      selected: false,
    };
  });

  // Обновляем каждого контрибьютера с количеством мерджей
  const res = contributors.map((contributor: Contributor) => {
    const id = contributor.id;
    const mergeCount = mergeCountMap.get(id) || 0;

    return {
      ...contributor,
      mergeCount,
    };
  });

  return res;
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
): Promise<Map<number, number>> => {
  // Создаем Map для хранения количества мерджей для каждого пользователя
  const mergeCountMap = new Map<number, number>();

  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = `+merged:${startDate}..${endDate}`;
  }

  // Получаем все смерженные PR для репозитория с фильтром по датам
  const { data } = await githubClient.get(
    `https://api.github.com/search/issues?q=repo:${owner}/${repo}+is:pr+is:merged${dateFilter}&per_page=100`,
  );

  if (data && data.items) {
    // Для каждого PR получаем информацию о пользователе и увеличиваем счетчик
    for (const pr of data.items) {
      const userId = pr.user.id;
      mergeCountMap.set(userId, (mergeCountMap.get(userId) || 0) + 1);
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
  const { data } = await githubClient.get(
    `https://api.github.com/search/issues?q=repo:${owner}/${repo}+author:${contributor}+is:pr+is:merged+${dateFilter}`,
  );

  return data.items;
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
  const mergeCount = mergeCountMap.get(contributor.id) || 0;

  return {
    id: contributor.id,
    avatar: contributor.avatar_url,
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
