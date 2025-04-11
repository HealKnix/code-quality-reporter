import React, { useState, useRef } from 'react';
import Header from '../components/Layout/Header';
import RepositoryInput from '../components/Repository/RepositoryInput';
import ContributorsList from '../components/Contributors/ContributorsList';
import DateRangePicker from '../components/CodeReview/DateRangePicker';
import CodeReviewResults from '../components/CodeReview/CodeReviewResults';
import { Contributor, CodeReview } from '../types';
import {
  useRepositoryInfo,
  useContributors,
  useCodeReviews,
} from '../hooks/useGitHubQueries';
import { Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { DateRange } from 'react-day-picker';
import { getMergedPullRequests } from '../services/github.service';
import { Toaster } from '../components/ui/toaster';
import { useToast } from '../hooks/use-toast';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

const MainPage: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedContributors, setSelectedContributors] = useState<
    Contributor[]
  >([]);
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [codeReviews, setCodeReviews] = useState<CodeReview[]>([]);
  const { toast } = useToast();
  const contributorsRef = useRef<HTMLDivElement>(null);

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

  const { data: contributors = [], isLoading: isLoadingContributors } =
    useContributors(owner, repo);

  const codeReviewMutation = useCodeReviews({
    onSuccess: (data) => {
      setCodeReviews(data);
    },
    onError: (error: Error) => {
      console.error('Error performing code reviews:', error);
      // Показываем toast с ошибкой
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: error.message,
      });
    },
  });

  const handleRepositorySubmit = (inputRepoUrl: string) => {
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

  const handleDateRangeChange = (range: DateRange | undefined) => {
    setDateRange(range);
  };

  // Форматирование периода для отображения
  const formatDateRange = (range?: DateRange) => {
    if (!range?.from || !range?.to) return '';

    const fromFormatted = format(range.from, 'dd.MM.yyyy', { locale: ru });
    const toFormatted = format(range.to, 'dd.MM.yyyy', { locale: ru });

    return `${fromFormatted} - ${toFormatted}`;
  };

  const handleGenerateReview = async () => {
    if (
      !repoInfo ||
      selectedContributors.length === 0 ||
      !dateRange?.from ||
      !dateRange?.to
    ) {
      return;
    }

    const startDate = dateRange.from.toISOString().split('T')[0];
    const endDate = dateRange.to.toISOString().split('T')[0];

    // Проверяем наличие мерджей у выбранных контрибьютеров за указанный период
    try {
      const mergeCountMap = await getMergedPullRequests(
        repoInfo.owner,
        repoInfo.repo,
        startDate,
        endDate,
      );

      // Проверяем каждого выбранного контрибьютера
      const contributorsWithNoMerges = selectedContributors.filter(
        (contributor) => {
          const mergeCount = mergeCountMap.get(contributor.login) || 0;
          return mergeCount === 0;
        },
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
          description: `Следующие контрибьютеры не имеют мерджей за выбранный период: ${noMergesNames}. Выберите другой период или других контрибьютеров.`,
        });

        // Прокручиваем страницу к списку контрибьютеров
        scrollToContributors();

        return; // Прерываем выполнение, не запускаем анализ
      }

      // Если у всех контрибьютеров есть мерджи, продолжаем с анализом
      const contributorIds = selectedContributors.map((c) => c.id);

      codeReviewMutation.mutate({
        owner: repoInfo.owner,
        repo: repoInfo.repo,
        contributors: contributorIds,
        startDate,
        endDate,
      });
    } catch (error) {
      console.error('Error checking for merges:', error);
      // Показываем toast с ошибкой
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Ошибка при проверке мерджей. Попробуйте ещё раз.',
      });
      scrollToContributors();
    }
  };

  const isLoading =
    isLoadingRepo || isLoadingContributors || codeReviewMutation.isPending;
  const error = repoError || codeReviewMutation.error;

  // Если есть ошибка, показываем toast с ошибкой
  React.useEffect(() => {
    if (error) {
      let description =
        error instanceof Error ? error.message : 'Произошла ошибка';

      if (error instanceof Error && error.message.includes('rate limit')) {
        description = `${description}\nДостигнут лимит запросов к GitHub API. Вы можете подождать некоторое время или добавить GitHub токен в файл .env (REACT_APP_GITHUB_TOKEN)`;
      }

      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description,
      });
    }
  }, [error, toast]);

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <Header />

      {/* Добавляем компонент Toaster для отображения уведомлений */}
      <Toaster />

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
              <div ref={contributorsRef}>
                <ContributorsList
                  contributors={contributors}
                  onContributorSelect={handleContributorSelect}
                />
              </div>

              <DateRangePicker
                onDateRangeChange={(startDate, endDate) => {
                  if (startDate && endDate) {
                    setDateRange({
                      from: new Date(startDate),
                      to: new Date(endDate),
                    });
                  }
                }}
              />

              <div className="mb-6">
                <Button
                  onClick={handleGenerateReview}
                  disabled={
                    selectedContributors.length === 0 ||
                    !dateRange?.from ||
                    !dateRange?.to ||
                    codeReviewMutation.isPending
                  }
                  className="w-full md:w-auto"
                >
                  {codeReviewMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Анализирую...
                    </>
                  ) : (
                    'Закод-ревьюить'
                  )}
                </Button>
              </div>
            </>
          )}

          {codeReviews.length > 0 && (
            <CodeReviewResults
              reviews={codeReviews}
              dateRangeFormatted={formatDateRange(dateRange)}
            />
          )}
        </>
      )}
    </div>
  );
};

export default MainPage;
