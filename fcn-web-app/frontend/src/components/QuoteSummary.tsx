import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, Shield, Clock, DollarSign, Activity, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FCNParameters, QuoteResult } from '@/lib/fcn-calculations';
import { cn } from '@/lib/utils';

interface QuoteSummaryProps {
  params: FCNParameters;
  quote: QuoteResult;
}

interface MarketData {
  sofr: number | null;
  vix: number | null;
}

interface StockData {
  code: string;
  iv: number | null;
  hv: number | null;
  price: number | null;
}

export function QuoteSummary({ params, quote }: QuoteSummaryProps) {
  const [marketData, setMarketData] = useState<MarketData>({ sofr: null, vix: null });
  const [stocksData, setStocksData] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(false);

  // 獲取市場數據
  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        const response = await fetch('/api/market/params');
        if (response.ok) {
          const data = await response.json();
          setMarketData({
            sofr: data.SOFR_RATE,
            vix: data.VIX_INDEX,
          });
        }
      } catch (error) {
        console.error('Failed to fetch market data:', error);
      }
    };

    fetchMarketData();
  }, []);

  // 獲取股票數據
  useEffect(() => {
    const fetchStockData = async () => {
      if (params.underlyingAssets.length === 0) {
        setStocksData([]);
        return;
      }

      setLoading(true);
      try {
        const response = await fetch('/api/stocks/available');
        if (response.ok) {
          const allStocks = await response.json();
          const selectedStocksData = params.underlyingAssets.map(code => {
            const stock = allStocks.find((s: any) => s.code === code);
            return {
              code,
              iv: stock?.iv || null,
              hv: stock?.vol90d || null,
              price: stock?.price || null,
            };
          });
          setStocksData(selectedStocksData);
        }
      } catch (error) {
        console.error('Failed to fetch stock data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStockData();
  }, [params.underlyingAssets]);

  const riskColors = {
    Low: 'text-accent',
    Medium: 'text-[hsl(38,92%,50%)]',
    High: 'text-destructive',
  };

  const riskBgColors = {
    Low: 'bg-accent/10 border-accent/20',
    Medium: 'bg-[hsl(38,92%,50%)]/10 border-[hsl(38,92%,50%)]/20',
    High: 'bg-destructive/10 border-destructive/20',
  };

  const riskLabels = {
    Low: '低風險',
    Medium: '中風險',
    High: '高風險',
  };

  return (
    <Card className="card-gradient border-border/50 overflow-hidden">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <DollarSign className="h-5 w-5 text-primary" />
          參考報價
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main Coupon Display */}
        <div className="text-center py-6 rounded-xl bg-muted/30 border border-border/30">
          <p className="text-sm text-muted-foreground mb-1">年化票息率</p>
          <div className="flex items-baseline justify-center gap-1">
            <span className="text-5xl font-bold font-mono text-primary animate-fade-in">
              {quote.annualizedCoupon.toFixed(2)}
            </span>
            <span className="text-2xl text-primary">%</span>
            <span className="text-lg text-muted-foreground ml-1">p.a.</span>
          </div>
          <div className={cn(
            "inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full text-sm font-medium border",
            riskBgColors[quote.riskLevel]
          )}>
            {quote.riskLevel === 'Low' && <Shield className="h-4 w-4" />}
            {quote.riskLevel === 'Medium' && <AlertTriangle className="h-4 w-4" />}
            {quote.riskLevel === 'High' && <TrendingUp className="h-4 w-4" />}
            <span className={riskColors[quote.riskLevel]}>{riskLabels[quote.riskLevel]}</span>
          </div>
        </div>

        {/* Market Parameters */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-foreground flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            市場參數
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="stat-card">
              <p className="text-xs text-muted-foreground mb-1">SOFR 利率</p>
              <p className="font-mono text-sm font-medium text-primary">
                {marketData.sofr !== null ? `${marketData.sofr.toFixed(2)}%` : '-'}
              </p>
            </div>
            <div className="stat-card">
              <p className="text-xs text-muted-foreground mb-1">VIX 指數</p>
              <p className="font-mono text-sm font-medium text-primary">
                {marketData.vix !== null ? marketData.vix.toFixed(2) : '-'}
              </p>
            </div>
          </div>
        </div>

        {/* Stock Parameters */}
        {stocksData.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-foreground flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />
              標的資產參數
            </h4>
            <div className="space-y-2">
              {stocksData.map(stock => (
                <div key={stock.code} className="p-3 rounded-lg bg-muted/30 border border-border/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-sm font-bold text-primary">{stock.code}</span>
                    {stock.price && (
                      <span className="text-xs text-muted-foreground">
                        ${stock.price.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">隱含波動率 (IV)</span>
                      <span className={cn(
                        "font-mono font-medium",
                        stock.iv && stock.iv > 80 ? "text-destructive" : stock.iv && stock.iv > 50 ? "text-[hsl(38,92%,50%)]" : "text-foreground"
                      )}>
                        {stock.iv !== null ? `${stock.iv.toFixed(1)}%` : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">歷史波動率 (HV)</span>
                      <span className="font-mono font-medium">
                        {stock.hv !== null ? `${stock.hv.toFixed(1)}%` : '-'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="stat-card">
            <p className="text-xs text-muted-foreground mb-1">標的資產</p>
            <p className="font-mono text-sm font-medium">{params.underlyingAssets.join(' / ')}</p>
          </div>
          <div className="stat-card">
            <p className="text-xs text-muted-foreground mb-1">存續期間</p>
            <p className="font-mono text-sm font-medium flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {params.tenor} 個月
            </p>
          </div>
        </div>

        {/* Parameters Summary */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-foreground">結構摘要</h4>
          <div className="grid gap-2 text-sm">
            <div className="flex justify-between py-2 border-b border-border/30">
              <span className="text-muted-foreground">履約價</span>
              <span className="font-mono font-medium">{params.strikePrice}%</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/30">
              <span className="text-muted-foreground">敲出價</span>
              <span className="font-mono font-medium text-accent">{params.knockOutBarrier}%</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/30">
              <span className="text-muted-foreground">敲入價</span>
              <span className="font-mono font-medium text-destructive">{params.knockInBarrier}%</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/30">
              <span className="text-muted-foreground">障礙類型</span>
              <span className="font-mono font-medium">{params.barrierType === 'EKI' ? '歐式' : '美式'}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-muted-foreground">發行價格</span>
              <span className="font-mono font-medium">{params.issuePrice}%</span>
            </div>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}
