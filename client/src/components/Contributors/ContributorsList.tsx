import React, { useState } from 'react';
import { Contributor } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { DateRange } from 'react-day-picker';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { Loader2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';

// Компонент таблицы контрибьюторов
interface ContributorsTableProps {
  contributors: Contributor[];
  emailFilter: string;
  selectedContributors: Contributor[];
  onContributorToggle: (contributor: Contributor) => void;
}

const ContributorsTable = React.memo(
  ({
    contributors,
    emailFilter,
    selectedContributors,
    onContributorToggle,
  }: ContributorsTableProps) => {
    const filteredContributors = emailFilter.trim()
      ? contributors.filter(
          (c) =>
            c.email.toLowerCase().includes(emailFilter.toLowerCase()) ||
            c.name.toLowerCase().includes(emailFilter.toLowerCase()),
        )
      : contributors;

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
            {filteredContributors.length > 0 ? (
              filteredContributors.map((contributor) => (
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
                  className="text-center py-4 text-muted-foreground"
                >
                  Не найдено контрибьютеров по заданным критериям
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
  contributors: Contributor[];
  onContributorSelect: (selectedContributors: Contributor[]) => void;
  dateRange: DateRange | undefined;
  setDateRange: (dateRange: DateRange | undefined) => void;
  minDate?: Date;
  maxDate?: Date;
  onGenerateReview: () => void;
  isPending: boolean;
  selectedContributorsCount: number;
}

const ContributorsList: React.FC<ContributorsListProps> = ({
  contributors,
  onContributorSelect,
  dateRange,
  setDateRange,
  minDate,
  maxDate,
  onGenerateReview,
  isPending,
  selectedContributorsCount,
}) => {
  const [selectedContributors, setSelectedContributors] = useState<
    Contributor[]
  >([]);
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

  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-center justify-between pb-2 flex-wrap">
        <CardTitle className="text-xl">Контрибьютеры</CardTitle>
        <div className="flex items-center gap-2">
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
        <div className="space-y-4">
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
          />

          <Button
            onClick={onGenerateReview}
            disabled={
              selectedContributorsCount === 0 ||
              !dateRange?.from ||
              !dateRange?.to ||
              isPending
            }
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
