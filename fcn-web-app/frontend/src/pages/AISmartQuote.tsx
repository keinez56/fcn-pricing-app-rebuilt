import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Sparkles, Menu, X, Settings2, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StockPoolSelect } from '@/components/ai-fcn/StockPoolSelect';
import { BasketSizeSelect } from '@/components/ai-fcn/BasketSizeSelect';
import { TopPicksSection } from '@/components/ai-fcn/TopPicksSection';
import { AllQuotesGrid } from '@/components/ai-fcn/AllQuotesGrid';
import { LoadingOverlay } from '@/components/ai-fcn/LoadingOverlay';
import { generateBatchQuotes, type FCNQuote, type AIFCNParams, type BatchQuoteResponse } from '@/lib/ai-fcn-utils';
import { useToast } from '@/hooks/use-toast';

export default function AISmartQuote() {
  const { toast } = useToast();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [quotes, setQuotes] = useState<FCNQuote[]>([]);
  const [response, setResponse] = useState<BatchQuoteResponse | null>(null);

  const [params, setParams] = useState<AIFCNParams>({
    selectedStocks: [],
    basketSizes: [2, 3],
    strikePrice: 80,
    knockIn: 65,
    knockOut: 103,
    tenor: 6,
    nonCallPeriods: 1,
    kiType: 'EKI',
    cost: 99.0,
  });

  // 自動調整閉鎖期不超過承作期間
  const handleTenorChange = (value: number) => {
    setParams(p => ({
      ...p,
      tenor: value,
      nonCallPeriods: Math.min(p.nonCallPeriods, value),
    }));
  };

  const handleGenerate = useCallback(async () => {
    if (params.selectedStocks.length === 0) {
      toast({
        title: '請選擇股票',
        description: '至少需要選擇一檔標的',
        variant: 'destructive',
      });
      return;
    }

    if (params.basketSizes.length === 0) {
      toast({
        title: '請選擇組合大小',
        description: '至少需要選擇一種連結標的數量',
        variant: 'destructive',
      });
      return;
    }

    // 驗證價格邏輯
    if (params.knockIn >= params.strikePrice) {
      toast({
        title: '參數錯誤',
        description: '敲入價必須低於履約價',
        variant: 'destructive',
      });
      return;
    }

    if (params.knockOut <= params.strikePrice) {
      toast({
        title: '參數錯誤',
        description: '敲出價必須高於履約價',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);

    try {
      const result = await generateBatchQuotes(params);
      setQuotes(result.quotes);
      setResponse(result);

      toast({
        title: 'AI 報價產生完成',
        description: `共產生 ${result.totalCount} 種組合`,
      });
    } catch (error: any) {
      toast({
        title: '計算失敗',
        description: error.message || '請稍後再試',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [params, toast]);

  return (
    <div className="min-h-screen bg-gray-50">
      <AnimatePresence>
        {loading && <LoadingOverlay />}
      </AnimatePresence>

      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur">
        <div className="flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
            <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-gray-900">
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">返回</span>
            </Link>
            <div className="h-4 w-px bg-gray-200" />
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              AI 智慧詢價
            </h1>
          </div>
          {response && (
            <Badge variant="outline" className="text-xs">
              定價日: {response.pricingDate}
            </Badge>
          )}
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`
            fixed inset-y-0 left-0 z-30 mt-14 w-80 transform border-r bg-white transition-transform duration-300 lg:relative lg:mt-0 lg:translate-x-0
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
        >
          <div className="h-full overflow-y-auto p-4 space-y-6">
            <div className="flex items-center gap-2">
              <Settings2 className="h-5 w-5 text-blue-600" />
              <h2 className="font-semibold">AI FCN 參數</h2>
            </div>

            {/* 股票池選擇 */}
            <StockPoolSelect
              selected={params.selectedStocks}
              onChange={(stocks) => setParams(p => ({ ...p, selectedStocks: stocks }))}
            />

            {/* 組合大小選擇 */}
            <BasketSizeSelect
              selected={params.basketSizes}
              onChange={(sizes) => setParams(p => ({ ...p, basketSizes: sizes }))}
              maxSize={params.selectedStocks.length}
            />

            {/* 風險參數 */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium flex items-center gap-1">
                風險參數
                <Info className="h-3 w-3 text-gray-400" />
              </h3>

              {/* 履約價 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">履約價 (Strike)</span>
                  <span className="font-mono font-medium">{params.strikePrice}%</span>
                </div>
                <Slider
                  value={[params.strikePrice]}
                  onValueChange={([v]) => setParams(p => ({ ...p, strikePrice: v }))}
                  min={50}
                  max={100}
                  step={5}
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* 敲入價 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">敲入價 (KI)</span>
                  <span className="font-mono font-medium">{params.knockIn}%</span>
                </div>
                <Slider
                  value={[params.knockIn]}
                  onValueChange={([v]) => setParams(p => ({ ...p, knockIn: v }))}
                  min={50}
                  max={85}
                  step={5}
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>50%</span>
                  <span>85%</span>
                </div>
              </div>

              {/* 敲出價 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">敲出價 (KO)</span>
                  <span className="font-mono font-medium">{params.knockOut}%</span>
                </div>
                <Slider
                  value={[params.knockOut]}
                  onValueChange={([v]) => setParams(p => ({ ...p, knockOut: v }))}
                  min={100}
                  max={120}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>100%</span>
                  <span>120%</span>
                </div>
              </div>

              {/* 承作期間 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">承作期間</span>
                  <span className="font-mono font-medium">{params.tenor} 個月</span>
                </div>
                <Slider
                  value={[params.tenor]}
                  onValueChange={([v]) => handleTenorChange(v)}
                  min={2}
                  max={12}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>2M</span>
                  <span>12M</span>
                </div>
              </div>

              {/* 閉鎖期 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">閉鎖期</span>
                  <span className="font-mono font-medium">
                    {params.nonCallPeriods} 個月
                    {params.nonCallPeriods === params.tenor && (
                      <span className="text-amber-600 text-xs ml-1">(不觸發KO)</span>
                    )}
                  </span>
                </div>
                <Slider
                  value={[params.nonCallPeriods]}
                  onValueChange={([v]) => setParams(p => ({ ...p, nonCallPeriods: v }))}
                  min={1}
                  max={params.tenor}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>1M</span>
                  <span>{params.tenor}M</span>
                </div>
              </div>

              {/* KI 類型 */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">KI 類型</span>
                </div>
                <Select
                  value={params.kiType}
                  onValueChange={(v) => setParams(p => ({ ...p, kiType: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EKI">歐式 (EKI) - 到期日觀察</SelectItem>
                    <SelectItem value="AKI">美式 (AKI) - 每日觀察</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 產生按鈕 */}
            <Button
              onClick={handleGenerate}
              disabled={loading || params.selectedStocks.length === 0}
              className="w-full h-12 text-lg gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              <Sparkles className="h-5 w-5" />
              產生智慧報價
            </Button>

            {/* 市場參數資訊 */}
            {response && (
              <Card className="bg-gray-50">
                <CardHeader className="py-3">
                  <CardTitle className="text-sm">市場參數</CardTitle>
                </CardHeader>
                <CardContent className="py-2 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-500">SOFR 利率</span>
                    <span className="font-mono">{response.marketParams.SOFR_RATE.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">VIX 指數</span>
                    <span className="font-mono">{response.marketParams.VIX_INDEX.toFixed(2)}</span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </aside>

        {/* 手機版遮罩 */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* 主內容區 */}
        <main className="flex-1 min-h-[calc(100vh-3.5rem)] p-4 lg:p-6">
          {quotes.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full min-h-[400px] text-center"
            >
              <div className="h-24 w-24 rounded-full bg-blue-100 flex items-center justify-center mb-6">
                <Sparkles className="h-12 w-12 text-blue-600" />
              </div>
              <h2 className="text-2xl font-semibold mb-2">AI 智慧詢價</h2>
              <p className="text-gray-500 max-w-md">
                選擇您感興趣的股票池和風險參數，AI 將為您產生最佳收益組合推薦
              </p>
              <div className="mt-6 text-sm text-gray-400">
                <p>1. 從左側選擇股票池</p>
                <p>2. 設定組合大小和風險參數</p>
                <p>3. 點擊「產生智慧報價」</p>
              </div>
            </motion.div>
          ) : (
            <div className="space-y-8">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">AI 市場推薦</h2>
                  <p className="text-gray-500">
                    共 {quotes.length} 種組合，依票息率排序
                  </p>
                </div>
                <div className="text-right text-sm text-gray-500">
                  <p>履約價: {params.strikePrice}% | KI: {params.knockIn}% | KO: {params.knockOut}%</p>
                  <p>期間: {params.tenor}個月 | 閉鎖期: {params.nonCallPeriods}個月</p>
                </div>
              </div>

              <TopPicksSection quotes={quotes} />
              <AllQuotesGrid quotes={quotes} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
