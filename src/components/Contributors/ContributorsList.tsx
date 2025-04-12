import React, { useState } from 'react';
import { Contributor } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface ContributorsListProps {
  contributors: Contributor[];
  onContributorSelect: (selectedContributors: Contributor[]) => void;
}

const ContributorsList: React.FC<ContributorsListProps> = ({
  contributors,
  onContributorSelect,
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

  const filteredContributors = emailFilter.trim()
    ? contributors.filter(
        (c) =>
          c.email.toLowerCase().includes(emailFilter.toLowerCase()) ||
          c.name.toLowerCase().includes(emailFilter.toLowerCase()),
      )
    : contributors;

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-xl">Контрибьютеры</CardTitle>
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
                        selectedContributors.some(
                          (c) => c.id === contributor.id,
                        )
                          ? 'bg-muted/50'
                          : ''
                      }
                    >
                      <TableCell className="text-center">
                        <Checkbox
                          checked={selectedContributors.some(
                            (c) => c.id === contributor.id,
                          )}
                          onCheckedChange={() =>
                            handleContributorToggle(contributor)
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Avatar>
                          <AvatarImage
                            src={contributor.avatar}
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
        </div>
      </CardContent>
    </Card>
  );
};

export default ContributorsList;
