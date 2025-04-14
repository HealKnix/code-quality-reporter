import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { RepositoryInfoReturn } from '@/hooks/useGitHubQueries';
import { Contributor } from '@/types';
import { Loader2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { DateRange } from 'react-day-picker';

// Компонент таблицы контрибьюторов
interface ContributorsTableProps {
  contributors: Contributor[];
  emailFilter: string;
  selectedContributors: Contributor[];
  onContributorToggle: (contributor: Contributor) => void;
  isLoadingContributors: boolean;
}

const ContributorsTable = React.memo(
  ({
    contributors,
    emailFilter,
    selectedContributors,
    onContributorToggle,
    isLoadingContributors,
  }: ContributorsTableProps) => {
    const filteredContributors = emailFilter.trim()
      ? contributors.filter(
          (c) =>
            c.email.toLowerCase().includes(emailFilter.toLowerCase()) ||
            c.name.toLowerCase().includes(emailFilter.toLowerCase()),
        )
      : contributors;

    const sortedContributors = filteredContributors.sort(
      (a, b) => b.mergeCount - a.mergeCount,
    );

    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">Выбор</TableHead>
              <TableHead className="w-[80px]">Аватарка</TableHead>
              <TableHead>Имя</TableHead>
              <TableHead>Почта</TableHead>
              <TableHead className="text-right">Всего мерджей</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedContributors.length > 0 ? (
              sortedContributors.map((contributor) => (
                <TableRow
                  key={contributor.id}
                  className={
                    selectedContributors.some((c) => c.id === contributor.id)
                      ? 'bg-muted/50'
                      : ''
                  }
                >
                  <TableCell className="text-center">
                    <Checkbox
                      checked={selectedContributors.some(
                        (c) => c.id === contributor.id,
                      )}
                      onCheckedChange={() => onContributorToggle(contributor)}
                    />
                  </TableCell>
                  <TableCell>
                    <Avatar>
                      <AvatarImage
                        src={contributor.avatar_url}
                        alt={contributor.name}
                      />
                      <AvatarFallback>
                        {contributor.name.substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  </TableCell>
                  <TableCell>{contributor.name}</TableCell>
                  <TableCell className="text-primary">
                    {contributor.email}
                  </TableCell>
                  <TableCell className="text-right">
                    {contributor.mergeCount}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center py-2 text-muted-foreground"
                >
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="mt-4 text-muted-foreground">
                      Загружаем контрибьютеров
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    );
  },
);

interface ContributorsListProps {
  repo: RepositoryInfoReturn;
  contributors: Contributor[];
  onContributorSelect: (selectedContributors: Contributor[]) => void;
  dateRange: DateRange | undefined;
  setDateRange: (dateRange: DateRange | undefined) => void;
  minDate?: Date;
  maxDate?: Date;
  onGenerateReview: () => void;
  isPending: boolean;
  isLoadingContributors: boolean;
  selectedContributors: Contributor[];
  setSelectedContributors: (selectedContributors: Contributor[]) => void;
}

const ContributorsList: React.FC<ContributorsListProps> = ({
  repo,
  contributors,
  onContributorSelect,
  dateRange,
  setDateRange,
  minDate,
  maxDate,
  onGenerateReview,
  isPending,
  isLoadingContributors,
  selectedContributors,
  setSelectedContributors,
}) => {
  const [emailFilter, setEmailFilter] = useState('');

  const handleContributorToggle = (contributor: Contributor) => {
    const isSelected = selectedContributors.some(
      (c) => c.id === contributor.id,
    );
    let updatedSelection;

    if (isSelected) {
      updatedSelection = selectedContributors.filter(
        (c) => c.id !== contributor.id,
      );
    } else {
      updatedSelection = [...selectedContributors, contributor];
    }

    setSelectedContributors(updatedSelection);
    onContributorSelect(updatedSelection);
  };

  useEffect(() => {
    if (isLoadingContributors) {
      setSelectedContributors([]);
    }
  }, [isLoadingContributors]);

  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-center justify-between pb-2 flex-wrap">
        <CardTitle className="text-xl mb-4">
          Контрибьютеры ({repo.repoData.name})
        </CardTitle>
        <div className="items-center gap-2">
          <Label>Период мерджей</Label>
          <DateRangePicker
            dateRange={dateRange}
            setDateRange={setDateRange}
            min={minDate}
            max={maxDate}
            className="ml-auto"
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 mt-2">
          <div className="grid gap-2">
            <Label htmlFor="emailFilter">Почта контрибьютера</Label>
            <Input
              id="emailFilter"
              value={emailFilter}
              onChange={(e) => setEmailFilter(e.target.value)}
              placeholder="Введите почту..."
            />
          </div>

          <ContributorsTable
            contributors={contributors}
            emailFilter={emailFilter}
            selectedContributors={selectedContributors}
            onContributorToggle={handleContributorToggle}
            isLoadingContributors={isLoadingContributors}
          />

          <Button
            onClick={onGenerateReview}
            disabled={selectedContributors.length === 0 || isPending}
            className="w-full"
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Анализирую...
              </>
            ) : (
              'Закод-ревьюить'
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default ContributorsList;
