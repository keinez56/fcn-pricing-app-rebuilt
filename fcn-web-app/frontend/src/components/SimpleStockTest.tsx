import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const SimpleStockTest: React.FC = () => {
  const [stocks, setStocks] = useState<string[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchStocks();
  }, []);

  const fetchStocks = async () => {
    try {
      console.log('開始載入股票...');
      const response = await fetch('/api/stocks/available', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors', // 明確指定CORS模式
      });
      console.log('Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('載入成功:', data);
        setStocks(data);
      } else {
        setError(`API錯誤: ${response.status}`);
      }
    } catch (err) {
      console.error('載入失敗:', err);
      setError('網路連接失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (stock: string) => {
    console.log('選擇股票:', stock);
    if (!selectedStocks.includes(stock)) {
      setSelectedStocks([...selectedStocks, stock]);
    }
  };

  const handleRemove = (stock: string) => {
    setSelectedStocks(selectedStocks.filter(s => s !== stock));
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>股票測試組件</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <p>載入狀態: {loading ? '載入中...' : '完成'}</p>
            <p>錯誤: {error || '無'}</p>
            <p>可用股票數量: {stocks.length}</p>
            <p>已選股票數量: {selectedStocks.length}</p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded">
              錯誤: {error}
            </div>
          )}

          {!loading && stocks.length > 0 && (
            <div>
              <h4 className="font-medium mb-2">可用股票:</h4>
              <div className="flex flex-wrap gap-2">
                {stocks.slice(0, 8).map((stock) => (
                  <Button
                    key={stock}
                    size="sm"
                    variant={selectedStocks.includes(stock) ? "default" : "outline"}
                    onClick={() => handleSelect(stock)}
                  >
                    {stock}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {selectedStocks.length > 0 && (
            <div>
              <h4 className="font-medium mb-2">已選股票:</h4>
              <div className="flex flex-wrap gap-2">
                {selectedStocks.map((stock) => (
                  <Button
                    key={stock}
                    size="sm"
                    variant="secondary"
                    onClick={() => handleRemove(stock)}
                  >
                    {stock} ×
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default SimpleStockTest;