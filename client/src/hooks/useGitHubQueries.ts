import {
  useMutation,
  UseMutationOptions,
  useQuery,
  UseQueryOptions,
} from '@tanstack/react-query';
import {
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
  contributors: number[];
  startDate: string;
  endDate: string;
}

/**
 * Hook for performing code reviews
 */
export const useCodeReviews = (
  options?: Omit<
    UseMutationOptions<CodeReview[], Error, CodeReviewParams>,
    'mutationFn'
  >,
) => {
  return useMutation<CodeReview[], Error, CodeReviewParams>({
    mutationFn: ({
      owner,
      repo,
      contributors,
      startDate,
      endDate,
    }: CodeReviewParams) =>
      performCodeReviews(owner, repo, contributors, startDate, endDate),
    ...options,
  });
};
