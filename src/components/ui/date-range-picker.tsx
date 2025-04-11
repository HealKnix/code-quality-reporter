import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Calendar as CalendarIcon } from 'lucide-react';
import { DateRange } from 'react-day-picker';

import { cn } from '../../lib/utils';
import { Button } from './button';
import { Calendar } from './calendar';
import { Popover, PopoverContent, PopoverTrigger } from './popover';

interface DateRangePickerProps {
  dateRange: DateRange | undefined;
  setDateRange: (date: DateRange | undefined) => void;
  className?: string;
}

export function DateRangePicker({
  dateRange,
  setDateRange,
  className,
}: DateRangePickerProps) {
  return (
    <div className={cn('grid gap-2', className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={'outline'}
            className={cn(
              'w-full justify-start text-left font-normal',
              !dateRange && 'text-muted-foreground',
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {dateRange?.from ? (
              dateRange.to ? (
                <>
                  {format(dateRange.from, 'dd.MM.yy', { locale: ru })} -{' '}
                  {format(dateRange.to, 'dd.MM.yy', { locale: ru })}
                </>
              ) : (
                format(dateRange.from, 'dd.MM.yy', { locale: ru })
              )
            ) : (
              <span>Выберите период мерджей</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            defaultMonth={dateRange?.from}
            selected={dateRange}
            onSelect={setDateRange}
            numberOfMonths={2}
            styles={{
              caption_label: { textTransform: 'capitalize' },
              head_cell: { width: '48px', overflow: 'hidden' },
            }}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
