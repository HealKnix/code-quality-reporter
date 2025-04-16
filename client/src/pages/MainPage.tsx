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
  useTaskStatus,
} from '@/hooks/useGitHubQueries';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Loader2 } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { DateRange } from 'react-day-picker';
import { CodeReview, Contributor } from '../types';

function MainPage() {
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedContributors, setSelectedContributors] = useState<
    Contributor[]
  >([]);
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [codeReviews, setCodeReviews] = useState<CodeReview[]>([]);
  const [email, setEmail] = useState('');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isReportGenerating, setIsReportGenerating] = useState(false);
  const [loadingContributors, setLoadingContributors] = useState<string[]>([]);
  const [processingContributors, setProcessingContributors] = useState<
    Set<string>
  >(new Set());
  const [showReportsSection, setShowReportsSection] = useState(false);
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
  }, [isLoadingContributors, setCodeReviews]);

  // Task status polling for async report generation
  const { data: taskStatus } = useTaskStatus(taskId || '', isReportGenerating);

  // Define code review mutation
  const codeReviewMutation = useCodeReviews();

  // Function to process a contributor's result
  const processContributorResult = (contributorLogin: string, result: any) => {
    // Find the contributor in the selected list
    const contributor = selectedContributors.find(
      (c: Contributor) => c.login === contributorLogin,
    );

    if (!contributor) return;

    // Create or update the review for this contributor
    const newReview: CodeReview = {
      id: contributor.id,
      login: contributor.login,
      avatar: contributor.avatar_url,
      name: result.contributor_name || contributor.name,
      email: result.contributor_email || contributor.email || email,
      mergeCount: result.total_count || contributor.mergeCount,
      rating: 8, // Default rating
      status: 'Хорошо' as 'Хорошо',
      details: {
        codeStyle: 8,
        bugFixes: 8,
        performance: 8,
        security: 8,
      },
    };

    // Update or add the review
    setCodeReviews((prev: CodeReview[]) => {
      const reviewIndex = prev.findIndex(
        (r: CodeReview) => r.login === contributor.login,
      );
      if (reviewIndex >= 0) {
        const updated = [...prev];
        updated[reviewIndex] = newReview;
        return updated;
      } else {
        return [...prev, newReview];
      }
    });
  };

  // Handle task status changes
  useEffect(() => {
    if (!taskStatus) return;

    // Check for individual contributor results
    if (taskStatus.results) {
      // Process each completed contributor's result
      Object.entries(taskStatus.results).forEach(
        ([contributorLogin, result]) => {
          processContributorResult(contributorLogin, result);
          // Remove this contributor from loading state
          setLoadingContributors((prev) =>
            prev.filter((login) => login !== contributorLogin),
          );
        },
      );
      // Object.entries(taskStatus.results).forEach(([results]) => {
      //   setLoadingContributors1((prev) => [
      //     ...prev,
      //     {
      //       id: results?.id,
      //       filename: results?.filename,
      //     },
      //   ]);
      // });
    }

    // Check for individual contributor result (single update)
    if (taskStatus.contributor_login && taskStatus.result) {
      processContributorResult(taskStatus.contributor_login, taskStatus.result);
      // Remove this contributor from loading state
      setLoadingContributors((prev) =>
        prev.filter((login) => login !== taskStatus.contributor_login),
      );
    }

    // Check for completed tasks
    if (taskStatus.status === 'completed') {
      // Task is completely done, no more polling needed
      setIsReportGenerating(false);

      toast({
        title: 'Отчеты готовы!',
        description: 'Все отчеты были успешно сгенерированы.',
      });

      // Clear the loading indicators for all contributors
      setLoadingContributors([]);

      // Process the results if they exist
      if (taskStatus.result) {
        // Single contributor result
        if (taskStatus.result.contributor_login) {
          processContributorResult(
            taskStatus.result.contributor_login,
            taskStatus.result,
          );
        }

        // Handle multi-contributor results
        if (
          taskStatus.completed_contributors &&
          Array.isArray(taskStatus.completed_contributors)
        ) {
          taskStatus.completed_contributors.forEach(
            (contributorLogin: string) => {
              // Try to find the result for this contributor
              const contributorResult = taskStatus.results?.[contributorLogin];
              if (contributorResult) {
                processContributorResult(contributorLogin, contributorResult);
              }
            },
          );
        }
      }
    }
    // Handle partial completion
    else if (taskStatus.status === 'partial') {
      // Some contributors are done, but not all
      if (taskStatus.completed_contributors) {
        // Update each completed contributor
        taskStatus.completed_contributors.forEach(
          (contributorLogin: string) => {
            // Try to find this contributor's result
            const contributorResult = taskStatus.results?.[contributorLogin];
            if (contributorResult) {
              // Remove from loading state
              setLoadingContributors((prev: string[]) =>
                prev.filter((login: string) => login !== contributorLogin),
              );
              // Process the result
              processContributorResult(contributorLogin, contributorResult);
            }
          },
        );
      }
    } else if (taskStatus.status === 'failed') {
      setIsReportGenerating(false);
      // Remove all pending contributors from loading state
      setLoadingContributors([]);
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: `Не удалось сгенерировать отчет: ${taskStatus.error || 'Неизвестная ошибка'}`,
      });
    } else if (taskStatus?.status === 'completed-email-failed') {
      setIsReportGenerating(false);
      // Remove all pending contributors from loading state
      setLoadingContributors([]);
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

    // Show reports section immediately
    setShowReportsSection(true);

    // Clear any previous loading states
    setLoadingContributors([]);
    setProcessingContributors(new Set());

    // Prepare empty report templates for each contributor
    const initialReviews: CodeReview[] = contributorLogins.map((login) => {
      const contributor = selectedContributors.find((c) => c.login === login);
      return {
        id: contributor?.id || 0,
        login: contributor?.login || '',
        avatar: contributor?.avatar_url || '',
        name: contributor?.name || '',
        email: contributor?.email || email,
        mergeCount: contributor?.mergeCount || 0,
        rating: 0,
        status: 'Хорошо' as 'Хорошо',
        details: {
          codeStyle: 0,
          bugFixes: 0,
          performance: 0,
          security: 0,
        },
      };
    });
    setCodeReviews(initialReviews);

    // Scroll to results section before starting the process
    scrollToResults();

    // Добавляем всех контрибьюторов в состояние загрузки
    setLoadingContributors(contributorLogins);

    try {
      // Отправляем один запрос для всех контрибьюторов вместо цикла
      const result = await codeReviewMutation.mutateAsync({
        owner: repoInfo.owner,
        repo: repoInfo.repo,
        contributors: contributorLogins, // Все выбранные контрибьюторы
        startDate,
        endDate,
        email: email || undefined,
      });

      // Если результат - асинхронная задача с task_id
      if (!Array.isArray(result) && 'task_id' in result) {
        setTaskId(result.task_id as string);
        setIsReportGenerating(true);

        toast({
          title: 'Отчеты генерируются',
          description: `Отчеты для выбранных контрибьютеров будут отправлены на указанную почту после завершения генерации.`,
        });
      } else {
        // Для синхронного режима обрабатываем результаты напрямую
        const reviews = result as CodeReview[];
        if (reviews.length > 0) {
          // Обновляем данные для всех контрибьюторов
          reviews.forEach((review) => {
            processContributorResult(review.login, review);
          });

          // Очищаем состояние загрузки
          setLoadingContributors([]);

          toast({
            title: 'Отчеты готовы',
            description: 'Все отчеты были успешно сгенерированы.',
          });
        }
      }
    } catch (error) {
      console.error(`Error processing contributors:`, error);
      // Очищаем состояние загрузки при ошибке
      setLoadingContributors([]);

      // Показываем уведомление об ошибке
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: `Не удалось сгенерировать отчеты: ${error instanceof Error ? error.message : 'Неизвестная ошибка'}`,
      });
    }
  };

  // Detect errors from API calls
  const error = repoError || (codeReviewMutation?.error as Error | undefined);

  // Если есть ошибка, показываем toast с ошибкой
  React.useEffect(() => {
    if (error) {
      let description =
        error instanceof Error ? error.message : 'Произошла ошибка';

      if (error instanceof Error && error.message.includes('rate limit')) {
        description = `${description}
Достигнут лимит запросов к GitHub API. Вы можете подождать некоторое время или вписать GitHub токен в поле "GitHub API Token"`;
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

              {(showReportsSection || codeReviews.length > 0) && (
                <div ref={resultsRef}>
                  <CodeReviewResults
                    reviews={codeReviews}
                    dateRangeFormatted={formatDateRange(dateRange)}
                    loadingContributors={loadingContributors}
                  />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

// Simple email validation function
const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export default MainPage;
