import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface RepositoryInputProps {
  onSubmit: (repoName: string) => void;
}

const RepositoryInput: React.FC<RepositoryInputProps> = ({ onSubmit }) => {
  const [repoName, setRepoName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoName.trim()) {
      onSubmit(repoName.trim());
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-xl">Информация о репозитории</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="repository">Название репозитория</Label>
              <Input
                id="repository"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                placeholder="Введите название или URL репозитория..."
              />
            </div>
            <Button type="submit">Подгрузить информацию</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default RepositoryInput;
