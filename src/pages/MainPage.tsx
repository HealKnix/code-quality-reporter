import React, { useState } from 'react';
import Header from '../components/Layout/Header';
import RepositoryInput from '../components/Repository/RepositoryInput';
import ContributorsList from '../components/Contributors/ContributorsList';
import DateRangePicker from '../components/CodeReview/DateRangePicker';
import CodeReviewResults from '../components/CodeReview/CodeReviewResults';
import { Contributor, CodeReview } from '../types';
import { useRepositoryInfo, useContributors, useCodeReviews } from '../hooks/useGitHubQueries';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { AlertTriangle } from 'lucide-react';
import { Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { DateRange } from 'react-day-picker';

const MainPage: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedContributors, setSelectedContributors] = useState<Contributor[]>([]);
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [codeReviews, setCodeReviews] = useState<CodeReview[]>([]);

  // React Query hooks
  const { 
    data: repoInfo,
    isLoading: isLoadingRepo,
    error: repoError
  } = useRepositoryInfo(repoUrl);

  // Only fetch contributors when we have repo info
  const owner = repoInfo?.owner || '';
  const repo = repoInfo?.repo || '';
  const hasRepoInfo = !!owner && !!repo;

  const {
    data: contributors = [],
    isLoading: isLoadingContributors
  } = useContributors(owner, repo);

  const codeReviewMutation = useCodeReviews({
    onSuccess: (data) => {
      setCodeReviews(data);
    },
    onError: (error: Error) => {
      console.error('Error performing code reviews:', error);
    }
  });

  const handleRepositorySubmit = (inputRepoUrl: string) => {
    setRepoUrl(inputRepoUrl);
    // The useRepositoryInfo hook will automatically fetch data based on the URL
  };

  const handleContributorSelect = (contributors: Contributor[]) => {
    setSelectedContributors(contributors);
  };

  const handleDateRangeChange = (range: DateRange | undefined) => {
    setDateRange(range);
    if (range?.from && range?.to) {
      // Convert to ISO format for API
      const startDate = range.from.toISOString().split('T')[0];
      const endDate = range.to.toISOString().split('T')[0];
    }
  };

  const handleGenerateReview = async () => {
    if (!repoInfo || selectedContributors.length === 0 || !dateRange?.from || !dateRange?.to) {
      return;
    }

    const contributorEmails = selectedContributors.map(c => c.email);
    const startDate = dateRange.from.toISOString().split('T')[0];
    const endDate = dateRange.to.toISOString().split('T')[0];
    
    codeReviewMutation.mutate({
      owner: repoInfo.owner,
      repo: repoInfo.repo,
      contributors: contributorEmails,
      startDate,
      endDate
    });
  };

  const isLoading = isLoadingRepo || isLoadingContributors || codeReviewMutation.isPending;
  const error = repoError || codeReviewMutation.error;

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <Header />
      
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'Произошла ошибка'}
            {error instanceof Error && error.message.includes('rate limit') && (
              <div className="mt-2">
                <p>Достигнут лимит запросов к GitHub API. Вы можете:</p>
                <ul className="list-disc list-inside mt-1">
                  <li>Подождать некоторое время</li>
                  <li>Добавить GitHub токен в файл .env (REACT_APP_GITHUB_TOKEN)</li>
                </ul>
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}
      
      <RepositoryInput onSubmit={handleRepositorySubmit} />
      
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-muted-foreground">Загрузка данных...</p>
        </div>
      ) : (
        <>
          {hasRepoInfo && contributors.length > 0 && (
            <>
              <ContributorsList 
                contributors={contributors} 
                onContributorSelect={handleContributorSelect} 
              />
              
              <DateRangePicker 
                onDateRangeChange={(startDate, endDate) => {
                  if (startDate && endDate) {
                    setDateRange({
                      from: new Date(startDate),
                      to: new Date(endDate)
                    });
                  }
                }} 
              />
              
              <div className="mb-6">
                <Button
                  onClick={handleGenerateReview}
                  disabled={selectedContributors.length === 0 || !dateRange?.from || !dateRange?.to || codeReviewMutation.isPending}
                  className="w-full md:w-auto"
                >
                  {codeReviewMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Анализирую...
                    </>
                  ) : 'Заход-ревьюить'}
                </Button>
              </div>
            </>
          )}
          
          {codeReviews.length > 0 && (
            <CodeReviewResults reviews={codeReviews} />
          )}
        </>
      )}
    </div>
  );
};

export default MainPage;
