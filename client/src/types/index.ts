import { ReactNode } from 'react';

export interface Contributor {
  id: number;
  login: string;
  avatar_url: string;
  name: string;
  email: string;
  mergeCount: number;
  selected?: boolean;
}

export interface CodeReview {
  id: string | number;
  login: string; // Added login field for identifying contributors
  avatar: string;
  name: string;
  email: string;
  mergeCount: number;
  status: 'Хорошо' | 'Средне' | 'Плохо';
  rating: number;
  report_file?: string;
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
  created_at: Date;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface Child {
  children: ReactNode;
}
