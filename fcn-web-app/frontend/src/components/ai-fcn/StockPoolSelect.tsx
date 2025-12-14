import { useEffect, useState } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { type Stock, fetchAvailableStocks, getStockColor, getStockName } from '@/lib/ai-fcn-utils';

const MAX_STOCKS = 20; // 最多選擇 20 檔股票

interface StockPoolSelectProps {
  selected: string[];
  onChange: (stocks: string[]) => void;
}

export function StockPoolSelect({ selected, onChange }: StockPoolSelectProps) {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isMaxReached = selected.length >= MAX_STOCKS;

  useEffect(() => {
    loadStocks();
  }, []);

  const loadStocks = async () => {
    try {
      setLoading(true);
      const data = await fetchAvailableStocks();
      // 過濾掉 IV 資料不完整的股票，並按 IV 排序
      const validStocks = data
        .filter(s => s.iv !== null && s.iv > 0)
        .sort((a, b) => (b.iv || 0) - (a.iv || 0));
      setStocks(validStocks);
      setError(null);
    } catch (err) {
      setError('載入股票清單失敗');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleStock = (code: string) => {
    if (selected.includes(code)) {
      onChange(selected.filter(s => s !== code));
    } else if (!isMaxReached) {
      onChange([...selected, code]);
    }
  };

  const clearAll = () => {
    onChange([]);
  };

  const selectHighIV = () => {
    // 選擇 IV > 50 的股票，最多 20 檔
    const highIV = stocks
      .filter(s => (s.iv || 0) > 50)
      .slice(0, MAX_STOCKS)
      .map(s => s.code);
    onChange(highIV);
  };

  const selectTop10 = () => {
    // 選擇 IV 最高的前 10 檔
    const top10 = stocks.slice(0, 10).map(s => s.code);
    onChange(top10);
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 text-sm p-4 border border-red-200 rounded-lg">
        {error}
        <button onClick={loadStocks} className="ml-2 underline">
          重試
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">股票池</label>
        <div className="flex gap-2 text-xs">
          <button onClick={selectTop10} className="text-blue-600 hover:underline">
            Top10
          </button>
          <span className="text-gray-400">|</span>
          <button onClick={selectHighIV} className="text-blue-600 hover:underline">
            高IV
          </button>
          <span className="text-gray-400">|</span>
          <button onClick={clearAll} className="text-gray-500 hover:text-gray-700">
            清除
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 max-h-[300px] overflow-y-auto">
        {stocks.map((stock) => {
          const isSelected = selected.includes(stock.code);
          const isDisabled = !isSelected && isMaxReached;
          const color = getStockColor(stock.code);

          return (
            <label
              key={stock.code}
              className={`
                flex items-center gap-2 p-2 rounded-lg border transition-all
                ${isDisabled
                  ? 'cursor-not-allowed opacity-50 border-gray-200'
                  : 'cursor-pointer'}
                ${isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-blue-300'
                }
              `}
            >
              <Checkbox
                checked={isSelected}
                disabled={isDisabled}
                onCheckedChange={() => toggleStock(stock.code)}
              />
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <Badge
                  variant="outline"
                  className="text-xs font-mono shrink-0"
                  style={{ borderColor: color, color: color }}
                >
                  {stock.code}
                </Badge>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs text-gray-600 truncate">
                    {getStockName(stock.code)}
                  </span>
                  {stock.iv && (
                    <span className="text-[10px] text-gray-400">
                      IV: {stock.iv.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            </label>
          );
        })}
      </div>

      <p className="text-xs text-gray-500">
        已選擇 <span className={`font-medium ${isMaxReached ? 'text-red-600' : 'text-blue-600'}`}>{selected.length}</span>/{MAX_STOCKS} 檔標的
        {isMaxReached && (
          <span className="text-red-600 ml-2">
            (已達上限)
          </span>
        )}
      </p>
    </div>
  );
}
