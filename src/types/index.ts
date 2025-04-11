import { ReactNode } from 'react';

export interface Contributor {
  id: number;
  login: string; 
  avatar: string;
  name: string;
  email: string;
  mergeCount: number;
  selected?: boolean;
}

export interface CodeReview {
  id: string | number;
  avatar: string;
  name: string;
  email: string;
  mergeCount: number;
  status: 'Норма' | 'Внимание' | 'Критично';
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

export interface Child {
  children: ReactNode;
}
