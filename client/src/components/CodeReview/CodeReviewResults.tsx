import { forwardRef, useEffect } from 'react';
import { CodeReview } from '@/types';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
// The toast import is removed as it's not used
import { DownloadIcon, Loader2 } from 'lucide-react';
import {
  RepositoryInfoReturn,
  TaskStatusResult,
} from '@/hooks/useGitHubQueries';

interface CodeReviewResultsProps {
  repoInfo: RepositoryInfoReturn;
  reviews: CodeReview[];
  dateRangeFormatted?: string;
  loadingContributors?: string[];
}

const CodeReviewResults = forwardRef<HTMLDivElement, CodeReviewResultsProps>(
  (
    { repoInfo, reviews, dateRangeFormatted = '', loadingContributors = [] },
    ref,
  ) => {
    // Function to get badge variant based on status
    const getStatusVariant = (status: string) => {
      switch (status) {
        case 'Хорошо':
          return 'success';
        case 'Средне':
          return 'warning';
        case 'Плохо':
          return 'destructive';
        default:
          return 'secondary';
      }
    };

    return (
      <Card className="mb-6" ref={ref}>
        <CardHeader>
          <CardTitle className="text-xl">
            Отчеты
            {dateRangeFormatted && (
              <span className="ml-2 text-base font-normal text-muted-foreground">
                за период {dateRangeFormatted}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">Аватарка</TableHead>
                <TableHead>Имя</TableHead>
                <TableHead>Почта</TableHead>
                <TableHead className="text-center">Мерджей за период</TableHead>
                <TableHead className="text-center">Статус</TableHead>
                <TableHead className="text-right">Рейтинг</TableHead>
                <TableHead className="text-right"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reviews.length > 0 ? (
                reviews.map((review) => (
                  <TableRow key={review.id}>
                    <TableCell>
                      <Avatar>
                        <AvatarImage src={review.avatar} alt={review.name} />
                        <AvatarFallback>
                          {review.name.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                    </TableCell>
                    <TableCell>{review.name}</TableCell>
                    <TableCell className="text-primary">
                      {review.email}
                    </TableCell>
                    <TableCell className="text-center">
                      {review.mergeCount}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant={getStatusVariant(review.status)}
                        className="font-medium"
                      >
                        -
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-medium">-</TableCell>
                    <TableCell className="text-right">
                      {loadingContributors.includes(review.login) ? (
                        <Button variant="outline" size="sm" disabled>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Генерация...
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" asChild>
                          <a
                            href={`${process.env.REACT_APP_API_BASE_URL}/api/download-report/${repoInfo.owner}/${repoInfo.repo}/${review.report_file}`}
                          >
                            <DownloadIcon className="mr-2 h-4 w-4" />
                            Скачать отчет
                          </a>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center py-4 text-muted-foreground"
                  >
                    Нет данных для отображения. Выберите контрибьютеров и период
                    для анализа.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    );
  },
);

CodeReviewResults.displayName = 'CodeReviewResults';

export default CodeReviewResults;
