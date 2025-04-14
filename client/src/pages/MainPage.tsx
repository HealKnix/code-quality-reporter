import CodeReviewResults from '@/components/CodeReview/CodeReviewResults';
import ContributorsList from '@/components/Contributors/ContributorsList';
import Header from '@/components/Layout/Header';
import RepositoryInput from '@/components/Repository/RepositoryInput';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import {
  TaskStatusResponse,
  useCodeReviews,
  useContributors,
  useRepositoryInfo,
  useTaskStatus,
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
  const [email, setEmail] = useState('');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isReportGenerating, setIsReportGenerating] = useState(false);
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

  // Task status polling for async report generation
  const { data: taskStatus } = useTaskStatus(taskId || '', isReportGenerating);

  // Handle task status changes
  useEffect(() => {
    if (taskStatus?.status === 'completed' && taskStatus.result) {
      setIsReportGenerating(false);

      toast({
        title: 'Отчет готов!',
        description:
          'Отчет был успешно сгенерирован и отправлен на указанную почту.',
      });

      if (Array.isArray(taskStatus.result.items)) {
        // Convert the result to CodeReview array format if needed
        setCodeReviews([
          {
            id: 0,
            avatar: selectedContributors[0]?.avatar_url || '',
            name:
              taskStatus.result.contributor_name ||
              selectedContributors[0]?.name ||
              '',
            email: taskStatus.result.contributor_email || email,
            mergeCount: taskStatus.result.total_count || 0,
            rating: 8, // Default rating
            status: 'Хорошо',
            details: {
              codeStyle: 8,
              bugFixes: 8,
              performance: 8,
              security: 8,
            },
          },
        ]);
        scrollToResults();
      }
    } else if (taskStatus?.status === 'failed') {
      setIsReportGenerating(false);
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: `Не удалось сгенерировать отчет: ${taskStatus.error || 'Неизвестная ошибка'}`,
      });
    } else if (taskStatus?.status === 'completed-email-failed') {
      setIsReportGenerating(false);
      toast({
        variant: 'warning',
        title: 'Отчет готов, но не отправлен',
        description:
          'Отчет был успешно сгенерирован, но не удалось отправить его на почту. Проверьте настройки сервера.',
      });
    } else if (taskStatus?.status === 'completed-no-email') {
      setIsReportGenerating(false);
      toast({
        variant: 'warning',
        title: 'Отчет готов, но не отправлен',
        description:
          'Отчет был успешно сгенерирован, но на сервере не настроена отправка электронных писем.',
      });
    }
  }, [taskStatus, toast, email, selectedContributors]);

  const codeReviewMutation = useCodeReviews({
    onSuccess: (data) => {
      // Handle task ID response (async mode)
      if (!Array.isArray(data) && 'task_id' in data) {
        setTaskId(data.task_id);
        setIsReportGenerating(true);

        toast({
          title: 'Отчет генерируется',
          description:
            'Отчет будет отправлен на указанную почту после завершения генерации.',
        });
        return;
      }

      // Handle array response (sync mode)
      const reviews = data as CodeReview[];

      if (reviews.some((c) => c.mergeCount === 0)) {
        // Формируем список контрибьютеров без мерджей
        const noMergesNames = reviews
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
        reviews
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

    // Validate email if provided
    if (email && !validateEmail(email)) {
      toast({
        variant: 'destructive',
        title: 'Неверный формат',
        description: 'Пожалуйста, введите корректный адрес электронной почты.',
      });
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
      email: email || undefined, // Only pass email if provided
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
                  email={email}
                  setEmail={setEmail}
                  isReportGenerating={isReportGenerating}
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

// Simple email validation function
const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export default MainPage;
