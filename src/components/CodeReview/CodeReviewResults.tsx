import React, { forwardRef, ForwardedRef } from 'react';
import { CodeReview } from '../../types';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
} from '../ui/card';
import { Button } from '../ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { Badge } from '../ui/badge';

interface CodeReviewResultsProps {
  reviews: CodeReview[];
  dateRangeFormatted?: string;
}

const CodeReviewResults = forwardRef<HTMLDivElement, CodeReviewResultsProps>(({
  reviews,
  dateRangeFormatted = '',
}, ref) => {
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
          Код-ревью
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
                  <TableCell className="text-primary">{review.email}</TableCell>
                  <TableCell className="text-center">
                    {review.mergeCount}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant={getStatusVariant(review.status)}
                      className="font-medium"
                    >
                      {review.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {review.rating.toFixed(1)}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={6}
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
      <CardFooter>
        <Button>Сформировать отчет</Button>
      </CardFooter>
    </Card>
  );
});

CodeReviewResults.displayName = 'CodeReviewResults';

export default CodeReviewResults;
