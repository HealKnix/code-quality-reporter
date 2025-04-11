import React from 'react';
import { Card, CardHeader, CardTitle } from '../ui/card';

const Header: React.FC = () => {
  return (
    <Card className="mb-8 border-none shadow-none">
      <CardHeader className="text-center">
        <CardTitle className="text-3xl font-bold">
          Анализатор качества кода для GitHub репозиториев
        </CardTitle>
      </CardHeader>
    </Card>
  );
};

export default Header;
