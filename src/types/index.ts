export interface Contributor {
  id: number;
  avatar: string;
  name: string;
  email: string;
  mergeCount: number;
  selected?: boolean;
}

export interface CodeReview {
  id: number;
  avatar: string;
  name: string;
  email: string;
  mergeCount: number;
  status: 'Нормас' | 'Внимание' | 'Критично';
  rating: number;
  details?: {
    codeStyle: number;
    bugFixes: number;
    performance: number;
    security: number;
  };
}

export interface Repository {
  name: string;
  url: string;
  platform: 'GitHub' | 'GitLab' | 'Bitbucket';
}

export interface DateRange {
  start: string;
  end: string;
}
