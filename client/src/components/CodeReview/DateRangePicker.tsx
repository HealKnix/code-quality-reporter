import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { DateRangePicker as ShadcnDateRangePicker } from '@/components/ui/date-range-picker';
import { DateRange } from 'react-day-picker';
import { format } from 'date-fns';

interface DateRangePickerProps {
  onDateRangeChange: (startDate: string, endDate: string) => void;
  min?: Date;
  max?: Date;
}

const DateRangePicker: React.FC<DateRangePickerProps> = ({
  onDateRangeChange,
  min,
  max,
}) => {
  const [dateRange, setDateRange] = useState<DateRange | undefined>();

  const handleDateRangeChange = (range: DateRange | undefined) => {
    setDateRange(range);

    if (range?.from && range?.to) {
      // Format dates to API format (YYYY-MM-DD)
      const startDate = format(range.from, 'yyyy-MM-dd');
      const endDate = format(range.to, 'yyyy-MM-dd');
      onDateRangeChange(startDate, endDate);
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-xl">Период анализа</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label>Выберите период мерджей</Label>
            <ShadcnDateRangePicker
              dateRange={dateRange}
              setDateRange={handleDateRangeChange}
              min={min}
              max={max}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DateRangePicker;
