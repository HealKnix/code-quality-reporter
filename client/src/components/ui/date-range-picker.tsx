import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';
import { DateRange } from 'react-day-picker';
import { useState, useEffect } from 'react';

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
  // Состояние для отслеживания открытия/закрытия попапа
  const [isOpen, setIsOpen] = useState(false);
  // Состояние для календаря (может быть сброшено при открытии)
  const [calendarSelection, setCalendarSelection] = useState<
    DateRange | undefined
  >(dateRange);

  // Обновляем выбор в календаре при изменении props
  useEffect(() => {
    if (!isOpen) {
      // Важно использовать функциональное обновление для избежания бесконечных циклов
      setCalendarSelection((prev) => {
        // Обновляем только если значения действительно отличаются
        if (JSON.stringify(prev) !== JSON.stringify(dateRange)) {
          return dateRange;
        }
        return prev;
      });
    }
  }, [dateRange, isOpen]);

  // Обработчик открытия попапа
  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);

    if (open) {
      // При открытии попапа показываем текущий выбранный диапазон
      setCalendarSelection(dateRange);
    } else {
      // При закрытии попапа восстанавливаем текущий диапазон в календаре
      // но не применяем его автоматически
      setCalendarSelection(dateRange);
    }
  };

  // Обработчик выбора в календаре
  const handleCalendarSelect = (range: DateRange | undefined) => {
    setCalendarSelection(range);
  };

  // Обработчик сброса к начальному диапазону
  const handleReset = () => {
    setCalendarSelection(undefined);
    setDateRange(undefined);
  };

  // Обработчик применения выбранного диапазона
  const handleApply = () => {
    if (calendarSelection) {
      setDateRange(calendarSelection);
      setIsOpen(false);
    }
  };

  return (
    <div className={cn('grid gap-2', className)}>
      <Popover open={isOpen} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={'outline'}
            size={'sm'}
            className={cn(
              'w-[250px] justify-start text-left font-normal text-sm',
              !dateRange && 'text-muted-foreground',
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
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
              <span>За всё время</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="end">
          <div className="p-3 border-b flex justify-between items-center">
            <span className="text-sm font-medium">Выберите период</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="h-8"
            >
              Сбросить
            </Button>
          </div>
          <Calendar
            initialFocus
            locale={ru}
            mode="range"
            defaultMonth={dateRange?.from}
            selected={calendarSelection}
            onSelect={handleCalendarSelect}
            disabled={(date) => {
              if (!min || !max) return true;
              return date > max || date < min;
            }}
            numberOfMonths={2}
          />
          <div className="p-3 border-t flex justify-between items-center">
            <div className="text-sm">
              {calendarSelection?.from && calendarSelection?.to ? (
                <span className="text-muted-foreground">
                  {format(calendarSelection.from, 'dd.MM.yyyy', { locale: ru })}{' '}
                  - {format(calendarSelection.to, 'dd.MM.yyyy', { locale: ru })}
                </span>
              ) : (
                <span className="text-muted-foreground">Выберите даты</span>
              )}
            </div>
            <Button
              variant="default"
              size="sm"
              onClick={handleApply}
              disabled={!calendarSelection?.from || !calendarSelection?.to}
              className="h-8"
            >
              Применить
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
