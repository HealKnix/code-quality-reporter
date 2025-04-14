import React from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';

const Header: React.FC = () => {
  return (
    <Card className="mb-8 border-none shadow-none">
      <CardHeader className="text-center p-0">
        <CardTitle className="text-3xl font-bold">
          Анализатор качества кода для{' '}
          <span className="relative">
            GitHub{' '}
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              className="absolute -right-2.5 -top-2 rotate-6 scale-75"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M9.937 15.5C9.84772 15.1539 9.66734 14.8381 9.41462 14.5854C9.1619 14.3327 8.84607 14.1523 8.5 14.063L2.365 12.481C2.26033 12.4513 2.16821 12.3882 2.10261 12.3014C2.03702 12.2146 2.00153 12.1088 2.00153 12C2.00153 11.8912 2.03702 11.7854 2.10261 11.6986C2.16821 11.6117 2.26033 11.5487 2.365 11.519L8.5 9.936C8.84595 9.8468 9.16169 9.66657 9.4144 9.41404C9.66711 9.1615 9.84757 8.84588 9.937 8.5L11.519 2.365C11.5484 2.25992 11.6114 2.16734 11.6983 2.10139C11.7853 2.03544 11.8914 1.99975 12.0005 1.99975C12.1096 1.99975 12.2157 2.03544 12.3027 2.10139C12.3896 2.16734 12.4526 2.25992 12.482 2.365L14.063 8.5C14.1523 8.84607 14.3327 9.16189 14.5854 9.41462C14.8381 9.66734 15.1539 9.84772 15.5 9.937L21.635 11.518C21.7405 11.5471 21.8335 11.61 21.8998 11.6971C21.9661 11.7841 22.0021 11.8906 22.0021 12C22.0021 12.1094 21.9661 12.2159 21.8998 12.3029C21.8335 12.39 21.7405 12.4529 21.635 12.482L15.5 14.063C15.1539 14.1523 14.8381 14.3327 14.5854 14.5854C14.3327 14.8381 14.1523 15.1539 14.063 15.5L12.481 21.635C12.4516 21.7401 12.3886 21.8327 12.3017 21.8986C12.2147 21.9646 12.1086 22.0002 11.9995 22.0002C11.8904 22.0002 11.7843 21.9646 11.6973 21.8986C11.6104 21.8327 11.5474 21.7401 11.518 21.635L9.937 15.5Z"
                fill="url(#paint0_linear_73_395)"
                stroke="url(#paint1_linear_73_395)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M20 3V7"
                stroke="#7F00EE"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M22 5H18"
                stroke="#7F00EE"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M4 17V19"
                stroke="#003F88"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M5 18H3"
                stroke="#003F88"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient
                  id="paint0_linear_73_395"
                  x1="12.0018"
                  y1="1.99975"
                  x2="12.0018"
                  y2="22.0002"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor="#7F00EE" />
                  <stop offset="1" stopColor="#003F88" />
                </linearGradient>
                <linearGradient
                  id="paint1_linear_73_395"
                  x1="12.0018"
                  y1="1.99975"
                  x2="12.0018"
                  y2="22.0002"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor="#7F00EE" />
                  <stop offset="1" stopColor="#003F88" />
                </linearGradient>
              </defs>
            </svg>
          </span>{' '}
          репозиториев
        </CardTitle>
      </CardHeader>
    </Card>
  );
};

export default Header;
