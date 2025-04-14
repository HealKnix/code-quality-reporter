import CodeReviewResults from '@/components/CodeReview/CodeReviewResults';
import ContributorsList from '@/components/Contributors/ContributorsList';
import Header from '@/components/Layout/Header';
import RepositoryInput from '@/components/Repository/RepositoryInput';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import {
  useCodeReviews,
  useContributors,
  useRepositoryInfo,
} from '@/hooks/useGitHubQueries';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Loader2 } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { DateRange } from 'react-day-picker';
import { CodeReview, Contributor } from '../types';

const MainPage: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedContributors, setSelectedContributors] = useState<
    Contributor[]
  >([]);
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [codeReviews, setCodeReviews] = useState<CodeReview[]>([]);
  const { toast } = useToast();
  const contributorsRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // React Query hooks
  const {
    data: repoInfo,
    isLoading: isLoadingRepo,
    error: repoError,
  } = useRepositoryInfo(repoUrl);

  // Only fetch contributors when we have repo info
  const owner = repoInfo?.owner || '';
  const repo = repoInfo?.repo || '';
  const hasRepoInfo = !!owner && !!repo;

  // Форматирование даты для API
  const startDate = dateRange?.from
    ? dateRange.from.toISOString().split('T')[0]
    : undefined;
  const endDate = dateRange?.to
    ? dateRange.to.toISOString().split('T')[0]
    : undefined;

  const { data: contributors = [], isLoading: isLoadingContributors } =
    useContributors(owner, repo, startDate, endDate);

  useEffect(() => {
    if (isLoadingContributors) {
      setCodeReviews([]);
    }
  }, [isLoadingContributors]);

  const codeReviewMutation = useCodeReviews({
    onSuccess: (data) => {
      if (data.some((c) => c.mergeCount === 0)) {
        // Формируем список контрибьютеров без мерджей
        const noMergesNames = data
          .filter((c) => c.mergeCount === 0)
          .map((c) => c.name)
          .join(', ');

        // Показываем toast с предупреждением
        toast({
          variant: 'warning',
          title: 'Предупреждение',
          description: (
            <>
              Следующие контрибьютеры не имеют мерджей за период (
              {formatDateRange(dateRange)}): <strong>{noMergesNames}</strong>.
              Выберите другой период или других контрибьютеров.
            </>
          ),
        });
      }
      setCodeReviews(
        data
          .filter((c) => c.mergeCount > 0)
          .sort((a, b) => b.rating - a.rating),
      );
      scrollToResults();
    },
    onError: (error: Error) => {
      console.error('Error performing code reviews:', error);
      // Показываем toast с ошибкой
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: `Ошибка при проверке мерджей. Попробуйте ещё раз.\n${error.message}`,
      });
      scrollToContributors();
    },
  });

  const handleRepositorySubmit = (inputRepoUrl: string) => {
    setCodeReviews([]);
    setSelectedContributors([]);
    setDateRange(undefined);
    setRepoUrl(inputRepoUrl);
    // The useRepositoryInfo hook will automatically fetch data based on the URL
  };

  const handleContributorSelect = (contributors: Contributor[]) => {
    setSelectedContributors(contributors);
  };

  const scrollToContributors = () => {
    if (contributorsRef.current) {
      contributorsRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const scrollToResults = () => {
    setTimeout(() => {
      window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth',
      });
    }, 1);
  };

  // Форматирование периода для отображения
  const formatDateRange = (range?: DateRange) => {
    if (!range?.from || !range?.to) return '';

    const fromFormatted = format(range.from, 'dd.MM.yyyy', { locale: ru });
    const toFormatted = format(range.to, 'dd.MM.yyyy', { locale: ru });

    return `${fromFormatted} - ${toFormatted}`;
  };

  const handleGenerateReview = async () => {
    if (!repoInfo || selectedContributors.length === 0) {
      return;
    }

    const startDate =
      dateRange?.from?.toISOString().split('T')[0] ??
      new Date(
        repoInfo?.repoData.created_at ?? new Date('2000-01-01'),
      ).toISOString();
    const endDate =
      dateRange?.to?.toISOString().split('T')[0] ?? new Date().toISOString();

    // Проверяем каждого выбранного контрибьютера
    const contributorsWithNoMerges = selectedContributors.filter(
      (contributor) => contributor.mergeCount === 0,
    );

    if (contributorsWithNoMerges.length > 0) {
      // Формируем список контрибьютеров без мерджей
      const noMergesNames = contributorsWithNoMerges
        .map((c) => c.name)
        .join(', ');

      // Показываем toast с предупреждением
      toast({
        variant: 'warning',
        title: 'Предупреждение',
        description: (
          <>
            Следующие контрибьютеры не имеют мерджей:{' '}
            <strong>{noMergesNames}</strong>. Выберите других контрибьютеров.
          </>
        ),
      });

      // Прокручиваем страницу к списку контрибьютеров
      scrollToContributors();

      if (selectedContributors.every((c) => c.mergeCount === 0)) {
        return; // Прерываем выполнение, не запускаем анализ
      }
    }

    // Если у всех контрибьютеров есть мерджи, продолжаем с анализом
    const contributorLogins = selectedContributors
      .filter((c) => c.mergeCount > 0)
      .map((c) => c.login);

    codeReviewMutation.mutate({
      owner: repoInfo.owner,
      repo: repoInfo.repo,
      contributors: contributorLogins,
      startDate,
      endDate,
    });
  };

  const error = repoError || codeReviewMutation.error;

  // Если есть ошибка, показываем toast с ошибкой
  React.useEffect(() => {
    if (error) {
      let description =
        error instanceof Error ? error.message : 'Произошла ошибка';

      if (error instanceof Error && error.message.includes('rate limit')) {
        description = `${description}\nДостигнут лимит запросов к GitHub API. Вы можете подождать некоторое время или вписать GitHub токен в поле "GitHub API Token"`;
      }

      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: description,
      });
    }
  }, [error, toast]);

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <Header />
      <Toaster />

      <RepositoryInput onSubmit={handleRepositorySubmit} />

      {isLoadingRepo ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-muted-foreground">Загрузка данных...</p>
        </div>
      ) : (
        <>
          {hasRepoInfo && repoInfo && (
            <>
              <div ref={contributorsRef}>
                <ContributorsList
                  repo={repoInfo}
                  contributors={contributors}
                  onContributorSelect={handleContributorSelect}
                  dateRange={dateRange}
                  setDateRange={setDateRange}
                  minDate={
                    new Date(
                      repoInfo?.repoData.created_at ?? new Date('2000-01-01'),
                    )
                  }
                  maxDate={new Date()}
                  onGenerateReview={handleGenerateReview}
                  isLoadingContributors={isLoadingContributors}
                  isPending={codeReviewMutation.isPending}
                  selectedContributors={selectedContributors}
                  setSelectedContributors={setSelectedContributors}
                />
              </div>

              {codeReviews.length > 0 && !codeReviewMutation.isPending && (
                <div ref={resultsRef}>
                  <CodeReviewResults
                    reviews={codeReviews}
                    dateRangeFormatted={formatDateRange(dateRange)}
                  />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

export default MainPage;
