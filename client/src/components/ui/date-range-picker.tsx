import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';
import { DateRange } from 'react-day-picker';

import { cn } from '@/lib/utils';
import { Button } from './button';
import { Calendar } from './calendar';
import { Popover, PopoverContent, PopoverTrigger } from './popover';
import { ru } from 'date-fns/locale';

interface DateRangePickerProps {
  dateRange: DateRange | undefined;
  setDateRange: (date: DateRange | undefined) => void;
  className?: string;
  min?: Date;
  max?: Date;
}

export function DateRangePicker({
  dateRange,
  setDateRange,
  className,
  min,
  max,
}: DateRangePickerProps) {
  return (
    <div className={cn('grid gap-2', className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={'outline'}
            className={cn(
              'w-[300px] justify-start text-left font-normal',
              !dateRange && 'text-muted-foreground',
            )}
          >
            <CalendarIcon />
            {dateRange?.from ? (
              dateRange.to ? (
                <>
                  {format(dateRange.from, 'LLL dd, y', { locale: ru })} -{' '}
                  {format(dateRange.to, 'LLL dd, y', { locale: ru })}
                </>
              ) : (
                format(dateRange.from, 'LLL dd, y', { locale: ru })
              )
            ) : (
              <span>Выбрать период</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            initialFocus
            locale={ru}
            mode="range"
            defaultMonth={dateRange?.from}
            selected={dateRange}
            onSelect={setDateRange}
            disabled={(date) => {
              if (!min || !max) return true;
              return date > max || date < min;
            }}
            numberOfMonths={2}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
