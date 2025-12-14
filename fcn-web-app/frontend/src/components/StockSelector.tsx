import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Search, X, TrendingUp, DollarSign } from 'lucide-react';
import { toast } from "@/hooks/use-toast";

interface Stock {
  code: string;
  price: number;
  vol90d: number;
}

interface StockSelectorProps {
  selectedStocks: string[];
  onStocksChange: (stocks: string[]) => void;
  maxSelections?: number;
  disabled?: boolean;
}

const StockSelector: React.FC<StockSelectorProps> = ({
  selectedStocks,
  onStocksChange,
  maxSelections = 5,
  disabled = false
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [stockDetails, setStockDetails] = useState<Record<string, Stock>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [availableStocks, setAvailableStocks] = useState<string[]>([]);

  // 防抖搜尋
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.length >= 1) {
        fetchSuggestions(searchQuery);
      } else {
        setSuggestions([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 載入可用股票清單
  useEffect(() => {
    fetchAvailableStocks();
  }, []);

  // 載入已選股票的詳細資訊
  useEffect(() => {
    if (selectedStocks.length > 0) {
      fetchStockDetails(selectedStocks);
    }
  }, [selectedStocks]);

  const fetchAvailableStocks = async () => {
    try {
      console.log('正在載入可用股票清單...');
      const response = await fetch('/api/stocks/available');
      if (response.ok) {
        const stocks = await response.json();
        console.log('成功載入股票:', stocks);
        // Extract stock codes from the response
        const stockCodes = stocks.map((stock: any) => stock.code);
        setAvailableStocks(stockCodes);
      } else {
        console.error('API response not ok:', response.status, response.statusText);
        toast({
          title: "載入失敗",
          description: `無法載入股票清單 (${response.status})`,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Failed to fetch available stocks:', error);
      toast({
        title: "錯誤",
        description: "無法載入可用股票清單 - 請檢查API連接",
        variant: "destructive"
      });
    }
  };

  const fetchSuggestions = async (query: string) => {
    try {
      console.log('搜尋查詢:', query, '可用股票數量:', availableStocks.length);
      // 使用本地篩選，從可用股票中篩選
      const filtered = availableStocks.filter(stock =>
        stock.toUpperCase().includes(query.toUpperCase())
      ).slice(0, 10);
      console.log('篩選結果:', filtered);
      setSuggestions(filtered);
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
    }
  };

  const fetchStockDetails = async (stockCodes: string[]) => {
    try {
      setIsLoading(true);
      console.log('正在獲取股票詳細資訊:', stockCodes);

      const response = await fetch('/api/stocks/details', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbols: stockCodes }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('成功載入股票詳細資訊:', data);

        const stockDetails: Record<string, Stock> = {};
        data.forEach((stock: any) => {
          stockDetails[stock.symbol] = {
            code: stock.symbol,
            price: stock.currentPrice || 100.0,
            vol90d: stock.vol_90d || stock.iv || 0,
          };
        });

        setStockDetails(prev => ({ ...prev, ...stockDetails }));
      } else {
        console.error('API response not ok:', response.status);
        toast({
          title: "載入股票詳細資訊失敗",
          description: `API 錯誤: ${response.status}`,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Failed to fetch stock details:', error);
      toast({
        title: "錯誤",
        description: "無法載入股票詳細資訊",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStockSelect = useCallback((stockCode: string) => {
    console.log('點擊股票:', stockCode, 'disabled:', disabled);

    if (disabled) {
      console.log('組件被禁用，無法選擇');
      return;
    }

    if (selectedStocks.includes(stockCode)) {
      console.log('股票已選擇:', stockCode);
      toast({
        title: "已選擇",
        description: `${stockCode} 已在選擇清單中`,
        variant: "destructive"
      });
      return;
    }

    if (selectedStocks.length >= maxSelections) {
      console.log('已達最大選擇數量');
      toast({
        title: "選擇已滿",
        description: `最多只能選擇 ${maxSelections} 檔股票`,
        variant: "destructive"
      });
      return;
    }

    console.log('新增股票到清單:', stockCode);
    const newStocks = [...selectedStocks, stockCode];
    onStocksChange(newStocks);
    setSearchQuery('');
    setSuggestions([]);

    toast({
      title: "新增成功",
      description: `已新增 ${stockCode} 到選擇清單`
    });
  }, [selectedStocks, onStocksChange, maxSelections, disabled]);

  const handleStockRemove = useCallback((stockCode: string) => {
    if (disabled) return;

    const newStocks = selectedStocks.filter(stock => stock !== stockCode);
    onStocksChange(newStocks);

    toast({
      title: "移除成功",
      description: `已從清單中移除 ${stockCode}`
    });
  }, [selectedStocks, onStocksChange, disabled]);

  const getStockInfo = (stockCode: string): Stock | null => {
    return stockDetails[stockCode] || null;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          股票選擇器
        </CardTitle>
        <CardDescription>
          搜尋並選擇 FCN 連結標的（最多 {maxSelections} 檔）
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 搜尋框 */}
        <div className="relative">
          <Label htmlFor="stock-search">搜尋股票代碼</Label>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input
              id="stock-search"
              type="text"
              placeholder="輸入股票代碼，如 AAPL, TSLA..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
              className="pl-10"
              disabled={disabled}
            />
          </div>

          {/* 搜尋建議下拉 */}
          {suggestions.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {suggestions.map((stock) => (
                <button
                  key={stock}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none border-b border-gray-100 last:border-b-0"
                  onClick={() => handleStockSelect(stock)}
                  disabled={selectedStocks.includes(stock)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">{stock}</span>
                    {selectedStocks.includes(stock) && (
                      <Badge variant="secondary" className="text-xs">已選擇</Badge>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 已選股票清單 */}
        <div>
          <Label className="text-sm font-medium">
            已選股票 ({selectedStocks.length}/{maxSelections})
          </Label>

          {selectedStocks.length === 0 ? (
            <div className="mt-2 p-4 border-2 border-dashed border-gray-200 rounded-lg text-center text-gray-500">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>尚未選擇任何股票</p>
              <p className="text-xs">請使用上方搜尋框新增股票</p>
            </div>
          ) : (
            <div className="mt-2 space-y-2">
              {selectedStocks.map((stockCode) => {
                const stockInfo = getStockInfo(stockCode);
                return (
                  <div
                    key={stockCode}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900">
                          {stockCode}
                        </span>
                        {isLoading && !stockInfo && (
                          <Badge variant="outline" className="text-xs">載入中...</Badge>
                        )}
                      </div>

                      {stockInfo && (
                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3" />
                            <span>${stockInfo.price?.toFixed(2) || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            <span>{stockInfo.vol90d?.toFixed(1) || 'N/A'}% 波動</span>
                          </div>
                        </div>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleStockRemove(stockCode)}
                      disabled={disabled}
                      className="h-8 w-8 p-0 hover:bg-red-100"
                    >
                      <X className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 調試信息 */}
        <div className="text-xs text-gray-400 p-2 bg-gray-50 rounded">
          調試: 可用股票數量: {availableStocks.length}, 已選數量: {selectedStocks.length}/{maxSelections}
        </div>

        {/* 快速選擇常用股票 */}
        {availableStocks.length > 0 && selectedStocks.length < maxSelections && (
          <div>
            <Label className="text-sm font-medium">快速選擇熱門股票</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {availableStocks.slice(0, 8).map((stock) => (
                <Button
                  key={stock}
                  variant={selectedStocks.includes(stock) ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => handleStockSelect(stock)}
                  disabled={disabled || selectedStocks.includes(stock)}
                  className="text-xs"
                >
                  {stock}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* 選擇狀態資訊 */}
        <div className="text-xs text-gray-500 bg-amber-50 p-2 rounded border border-amber-200">
          ⚠️ FCN 風險提示：多檔股票組合風險主要由「最差表現者」決定。即使選擇多檔低波動股票搭配一檔高波動股票，風險仍等同於單獨持有該高波動股票。
        </div>
      </CardContent>
    </Card>
  );
};

export default StockSelector;