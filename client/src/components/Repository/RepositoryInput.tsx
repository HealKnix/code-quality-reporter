import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface RepositoryInputProps {
  onSubmit: (repoName: string) => void;
}

const RepositoryInput: React.FC<RepositoryInputProps> = ({ onSubmit }) => {
  const [repoName, setRepoName] = useState('');
  const [githubToken, setGithubToken] = useState('');

  useEffect(() => {
    if (localStorage.getItem('githubToken')) {
      setGithubToken(localStorage.getItem('githubToken') ?? '');
    }
  }, []);

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
                type="text"
                value={repoName}
                onChange={(e) => setRepoName(e.currentTarget.value)}
                placeholder="Введите название или URL репозитория..."
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="github_token">GitHub API Token</Label>
              <Input
                id="github_token"
                type="password"
                value={githubToken}
                placeholder="Введите токен GitHub..."
                onChange={(e) => {
                  setGithubToken(e.currentTarget.value);
                }}
              />
            </div>
            <Button
              type="submit"
              onClick={() => {
                localStorage.setItem('githubToken', githubToken);
              }}
            >
              Подгрузить информацию
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default RepositoryInput;
