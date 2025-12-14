import React, { useState, useCallback, useRef, useEffect } from 'react';
import { X, Info, Search, ChevronDown, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getStockName } from '@/lib/ai-fcn-utils';

interface TickerInputProps {
  tickers: string[];
  onChange: (tickers: string[]) => void;
  maxTickers?: number;
}

interface TickerOption {
  code: string;
  name: string;
  iv: number | null;
}

export function TickerInput({ tickers, onChange, maxTickers = 4 }: TickerInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [allTickers, setAllTickers] = useState<TickerOption[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 從後端 API 獲取所有可用股票
  useEffect(() => {
    const fetchTickers = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/stocks/available');
        if (response.ok) {
          const data = await response.json();
          const tickerOptions = data.map((s: any) => ({
            code: s.code,
            name: getStockName(s.code),
            iv: s.iv,
          }));
          // 按字母 A-Z 排序
          tickerOptions.sort((a: TickerOption, b: TickerOption) => a.code.localeCompare(b.code));
          setAllTickers(tickerOptions);
        }
      } catch (error) {
        console.error('Failed to fetch tickers:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTickers();
  }, []);

  // 過濾符合搜尋條件的股票（以輸入字母開頭）
  const filteredTickers = allTickers.filter(t => {
    const searchTerm = inputValue.toUpperCase();
    const isAlreadySelected = tickers.includes(t.code);
    // 只匹配以搜尋字母開頭的股票代碼
    const matchesSearch = !searchTerm || t.code.startsWith(searchTerm);
    return !isAlreadySelected && matchesSearch;
  });

  const addTicker = useCallback((ticker: string) => {
    const normalized = ticker.toUpperCase().trim();
    if (normalized && !tickers.includes(normalized) && tickers.length < maxTickers) {
      onChange([...tickers, normalized]);
      setInputValue('');
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  }, [tickers, onChange, maxTickers]);

  const removeTicker = useCallback((ticker: string) => {
    onChange(tickers.filter(t => t !== ticker));
  }, [tickers, onChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(prev =>
        prev < filteredTickers.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => prev > 0 ? prev - 1 : 0);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && filteredTickers[highlightedIndex]) {
        addTicker(filteredTickers[highlightedIndex].code);
      } else if (inputValue) {
        addTicker(inputValue);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  };

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 輸入變化時開啟下拉選單
  useEffect(() => {
    if (inputValue) {
      setIsOpen(true);
      setHighlightedIndex(0);
    }
  }, [inputValue]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">標的資產</span>
        <Tooltip>
          <TooltipTrigger asChild>
            <Info className="h-4 w-4 text-muted-foreground cursor-help" />
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            <p>選擇最多 {maxTickers} 檔美股代碼。FCN 的表現與表現最差的標的資產連動。</p>
          </TooltipContent>
        </Tooltip>
        {loading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>

      <div className="flex flex-wrap gap-2 min-h-[40px] p-2 rounded-lg border border-border bg-muted/30">
        {tickers.map(ticker => (
          <span key={ticker} className="ticker-tag flex items-center gap-1.5 animate-fade-in">
            {ticker}
            <button
              onClick={() => removeTicker(ticker)}
              className="hover:text-destructive transition-colors"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}

        {tickers.length < maxTickers && (
          <div className="relative flex-1 min-w-[120px]">
            <div className="flex items-center gap-1">
              <Search className="h-3.5 w-3.5 text-muted-foreground" />
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsOpen(true)}
                placeholder="搜尋代碼..."
                className="h-7 flex-1 text-sm font-mono bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/50"
              />
              <ChevronDown
                className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`}
              />
            </div>

            {/* 下拉選單 */}
            {isOpen && filteredTickers.length > 0 && (
              <div
                ref={dropdownRef}
                className="absolute top-full left-0 right-0 mt-1 max-h-[300px] overflow-y-auto bg-popover border border-border rounded-lg shadow-lg z-50"
              >
                {filteredTickers.map((ticker, index) => (
                  <button
                    key={ticker.code}
                    onClick={() => addTicker(ticker.code)}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-muted/50 transition-colors ${
                      index === highlightedIndex ? 'bg-muted/50' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium">{ticker.code}</span>
                      <span className="text-xs text-muted-foreground">{ticker.name}</span>
                    </div>
                    {ticker.iv !== null && (
                      <span className={`text-xs font-mono ${ticker.iv > 80 ? 'text-destructive' : ticker.iv > 50 ? 'text-[hsl(38,92%,50%)]' : 'text-muted-foreground'}`}>
                        IV: {ticker.iv.toFixed(0)}%
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* 無搜尋結果 */}
            {isOpen && inputValue && filteredTickers.length === 0 && (
              <div
                ref={dropdownRef}
                className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg z-50"
              >
                <div className="px-3 py-2 text-sm text-muted-foreground">
                  找不到符合的股票，按 Enter 新增 "{inputValue}"
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {tickers.length >= maxTickers && (
        <p className="text-xs text-muted-foreground">
          已達最大選擇數量 ({maxTickers} 檔)
        </p>
      )}
    </div>
  );
}
