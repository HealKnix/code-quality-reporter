import {
  useMutation,
  UseMutationOptions,
  useQuery,
  UseQueryOptions,
} from '@tanstack/react-query';
import {
  checkReportStatus,
  getContributors,
  getRepository,
  parseRepositoryUrl,
  performCodeReviews,
} from '../services/github.service';
import { CodeReview, Contributor, Repository } from '../types';

// Define return type for repository info
export interface RepositoryInfoReturn {
  repoData: Repository;
  owner: string;
  repo: string;
}

/**
 * Hook for fetching repository information
 */
export const useRepositoryInfo = (
  repoUrl: string,
  options?: Omit<
    UseQueryOptions<
      RepositoryInfoReturn,
      Error,
      RepositoryInfoReturn,
      [string, string]
    >,
    'queryKey' | 'queryFn' | 'enabled'
  >,
) => {
  return useQuery<
    RepositoryInfoReturn,
    Error,
    RepositoryInfoReturn,
    [string, string]
  >({
    queryKey: ['repository', repoUrl],
    queryFn: async () => {
      const repoInfo = parseRepositoryUrl(repoUrl);
      if (!repoInfo) {
        throw new Error('Неверный формат URL репозитория');
      }

      const { owner, repo } = repoInfo;
      const data = await getRepository(owner, repo);

      return {
        repoData: data,
        owner,
        repo,
      };
    },
    enabled: !!repoUrl,
    ...options,
  });
};

/**
 * Hook for fetching contributors from a repository
 */
export const useContributors = (
  owner: string,
  repo: string,
  startDate?: string,
  endDate?: string,
  options?: Omit<
    UseQueryOptions<
      Contributor[],
      Error,
      Contributor[],
      [string, string, string, string | undefined, string | undefined]
    >,
    'queryKey' | 'queryFn' | 'enabled'
  >,
) => {
  return useQuery<
    Contributor[],
    Error,
    Contributor[],
    [string, string, string, string | undefined, string | undefined]
  >({
    queryKey: ['contributors', owner, repo, startDate, endDate],
    queryFn: () => getContributors(owner, repo, startDate, endDate),
    enabled: !!owner && !!repo,
    ...options,
  });
};

// Define the parameters type for code reviews
interface CodeReviewParams {
  owner: string;
  repo: string;
  contributors: string[];
  startDate: string;
  endDate: string;
  email?: string;
}

// Define task status response type
export interface TaskStatusResponse {
  status: string;
  result?: any;
  error?: string;
  // New fields for multi-contributor support
  results?: Record<string, any>;
  pending_contributors?: string[];
  completed_contributors?: string[];
  failed_contributors?: string[];
  contributor_login?: string;
}

/**
 * Hook for performing code reviews
 */
export const useCodeReviews = (
  options?: Omit<
    UseMutationOptions<
      CodeReview[] | TaskStatusResponse,
      Error,
      CodeReviewParams
    >,
    'mutationFn'
  >,
) => {
  return useMutation<
    CodeReview[] | TaskStatusResponse,
    Error,
    CodeReviewParams
  >({
    mutationFn: ({
      owner,
      repo,
      contributors,
      startDate,
      endDate,
      email,
    }: CodeReviewParams) =>
      performCodeReviews(owner, repo, contributors, startDate, endDate, email),
    ...options,
  });
};

/**
 * Hook for checking report task status
 */
export const useTaskStatus = (taskId: string, enabled: boolean = false) => {
  return useQuery<
    TaskStatusResponse,
    Error,
    TaskStatusResponse,
    [string, string]
  >({
    queryKey: ['taskStatus', taskId],
    queryFn: () => checkReportStatus(taskId),
    enabled: enabled && !!taskId,
    refetchInterval: enabled && !!taskId ? 3000 : false, // Poll every 3 seconds if enabled
  });
};
