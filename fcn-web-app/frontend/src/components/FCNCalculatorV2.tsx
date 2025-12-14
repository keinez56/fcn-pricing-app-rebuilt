import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Calculator, TrendingUp, AlertCircle, CheckCircle, Clock, Zap } from 'lucide-react';
import { toast } from "@/hooks/use-toast";
import StockSelector from './StockSelector';

interface FCNResult {
  annualized_yield: number;
  calibrated_yield?: number;
  model_used: string;
  has_calibration?: boolean;
  input_params: any;
  market_params: any;
  stock_info: any;
}

interface SystemStatus {
  status: string;
  model_available: boolean;
}

const FCNCalculatorV2: React.FC = () => {
  // 狀態管理
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [period, setPeriod] = useState<string>('');
  const [nonCallPeriods, setNonCallPeriods] = useState<string>('1');
  const [strikePrice, setStrikePrice] = useState<string>('');
  const [knockOutPrice, setKnockOutPrice] = useState<string>('');
  const [knockInPrice, setKnockInPrice] = useState<string>('');
  const [kiType, setKiType] = useState<string>('EKI');
  const [cost, setCost] = useState<string>('');
  const [results, setResults] = useState<FCNResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // 載入系統狀態
  useEffect(() => {
    fetchSystemStatus();
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/api/health');
      if (response.ok) {
        const status = await response.json();
        setSystemStatus(status);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  };

  const validateInputs = (): boolean => {
    if (selectedStocks.length === 0) {
      toast({
        title: "請選擇股票",
        description: "請至少選擇 1 檔股票（最多 3 檔）",
        variant: "destructive"
      });
      return false;
    }

    if (selectedStocks.length > 3) {
      toast({
        title: "股票數量超過限制",
        description: "最多只能選擇 3 檔股票",
        variant: "destructive"
      });
      return false;
    }

    if (!period || !strikePrice || !knockOutPrice || !knockInPrice || !cost) {
      toast({
        title: "參數不完整",
        description: "請填寫所有必要的 FCN 參數",
        variant: "destructive"
      });
      return false;
    }

    const strike = parseFloat(strikePrice);
    const ko = parseFloat(knockOutPrice);
    const ki = parseFloat(knockInPrice);
    const months = parseInt(period);
    const costValue = parseFloat(cost);
    const nonCall = parseInt(nonCallPeriods);

    // 檢查承作期間 (2-12個月)
    if (months < 2 || months > 12) {
      toast({
        title: "期間錯誤",
        description: "承作期間應在 2-12 個月之間",
        variant: "destructive"
      });
      return false;
    }

    // 檢查閉鎖期 (1-承作期間)
    if (nonCall < 1 || nonCall > months) {
      toast({
        title: "閉鎖期錯誤",
        description: `閉鎖期應在 1-${months} 個月之間`,
        variant: "destructive"
      });
      return false;
    }

    // 檢查轉換價範圍 (50%-100%)
    if (strike < 50 || strike > 100) {
      toast({
        title: "轉換價錯誤",
        description: "轉換價應在 50%-100% 之間",
        variant: "destructive"
      });
      return false;
    }

    // 檢查上限價範圍 (90%-150%)
    if (ko < 90 || ko > 150) {
      toast({
        title: "上限價錯誤",
        description: "上限價應在 90%-150% 之間",
        variant: "destructive"
      });
      return false;
    }

    // 檢查保護價範圍 (50%-95%)
    if (ki < 50 || ki > 95) {
      toast({
        title: "保護價錯誤",
        description: "保護價應在 50%-95% 之間",
        variant: "destructive"
      });
      return false;
    }

    // 檢查手續費成本範圍 (95%-99.8%, 對應5%-0.2%手續費)
    if (costValue < 95 || costValue > 99.8) {
      toast({
        title: "手續費錯誤",
        description: "手續費成本應在 95%-99.8% 之間 (對應5%-0.2%手續費)",
        variant: "destructive"
      });
      return false;
    }

    // 檢查價格邏輯關係
    if (ki >= strike) {
      toast({
        title: "參數錯誤",
        description: "保護價必須低於轉換價",
        variant: "destructive"
      });
      return false;
    }

    if (ko <= strike) {
      toast({
        title: "參數錯誤",
        description: "上限價必須高於轉換價",
        variant: "destructive"
      });
      return false;
    }

    return true;
  };

  const calculateFCN = async () => {
    if (!validateInputs()) return;

    setIsCalculating(true);
    setResults(null);

    try {
      const requestData = {
        stocks: selectedStocks,
        period: parseFloat(period),
        nonCallPeriods: parseInt(nonCallPeriods),
        strikePrice: parseFloat(strikePrice),
        knockOutPrice: parseFloat(knockOutPrice),
        knockInPrice: parseFloat(knockInPrice),
        kiType: kiType,
        customFeeRate: parseFloat(cost)
      };

      const response = await fetch('/api/fcn/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '計算失敗');
      }

      const result: FCNResult = await response.json();
      setResults(result);

      // 顯示計算完成通知
      const yieldText = result.has_calibration && result.calibrated_yield !== undefined
        ? `校準後年化收益率: ${result.calibrated_yield.toFixed(2)}% (原始: ${result.annualized_yield.toFixed(2)}%)`
        : `年化收益率: ${result.annualized_yield.toFixed(2)}%`;

      toast({
        title: "計算完成",
        description: `${yieldText} (使用模型: ${result.model_used})`,
        variant: "default"
      });

    } catch (error) {
      console.error('FCN calculation failed:', error);
      toast({
        title: "計算失敗",
        description: error instanceof Error ? error.message : "請檢查網路連接或聯絡技術支援",
        variant: "destructive"
      });
    } finally {
      setIsCalculating(false);
    }
  };


  return (
    <div className="space-y-6">
      {/* 系統狀態指示器 */}
      {systemStatus && systemStatus.status === 'healthy' && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-medium">系統運行正常</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>模型狀態: {systemStatus.model_available ? 'HistGradientBoosting 已載入' : '基本模式'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左側參數設定區 */}
        <div className="space-y-6">
          {/* 股票選擇器 */}
          <StockSelector
            selectedStocks={selectedStocks}
            onStocksChange={setSelectedStocks}
            maxSelections={3}
            disabled={isCalculating}
          />

          {/* FCN參數設定 */}
          <Card className="bg-white shadow-lg">
            <CardHeader className="bg-gradient-to-r from-purple-500 to-purple-600 text-white">
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                FCN 結構參數
              </CardTitle>
              <CardDescription className="text-purple-100">
                設定 Fixed Coupon Note 的結構化參數
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              {/* 期間設定 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="period">承作期間 (月)</Label>
                  <Input
                    id="period"
                    type="number"
                    placeholder="6"
                    value={period}
                    onChange={(e) => {
                      setPeriod(e.target.value);
                      // 如果閉鎖期大於承作期間，自動調整
                      const newPeriod = parseInt(e.target.value);
                      const currentNonCall = parseInt(nonCallPeriods);
                      if (currentNonCall > newPeriod) {
                        setNonCallPeriods(e.target.value);
                      }
                    }}
                    min="2"
                    max="12"
                    disabled={isCalculating}
                  />
                  <p className="text-xs text-gray-500 mt-1">範圍: 2-12 個月</p>
                </div>
                <div>
                  <Label htmlFor="nonCallPeriods">閉鎖期 (月)</Label>
                  <Input
                    id="nonCallPeriods"
                    type="number"
                    placeholder="1"
                    value={nonCallPeriods}
                    onChange={(e) => setNonCallPeriods(e.target.value)}
                    min="1"
                    max={period || "12"}
                    disabled={isCalculating}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {parseInt(nonCallPeriods) === parseInt(period) && period ? (
                      <span className="text-amber-600 font-medium">⚠️ 閉鎖期=承作期間，不會觸發 KO</span>
                    ) : (
                      `範圍: 1-${period || '?'} 個月`
                    )}
                  </p>
                </div>
              </div>

              {/* 價格參數 */}
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label htmlFor="strike">轉換價 (K) %</Label>
                  <Input
                    id="strike"
                    type="number"
                    placeholder="95"
                    value={strikePrice}
                    onChange={(e) => setStrikePrice(e.target.value)}
                    step="0.1"
                    min="50"
                    max="100"
                    disabled={isCalculating}
                  />
                  <p className="text-xs text-gray-500 mt-1">範圍: 50%-100%</p>
                </div>

                <div>
                  <Label htmlFor="knockout">上限價 (KO) %</Label>
                  <Input
                    id="knockout"
                    type="number"
                    placeholder="105"
                    value={knockOutPrice}
                    onChange={(e) => setKnockOutPrice(e.target.value)}
                    step="0.1"
                    min="90"
                    max="150"
                    disabled={isCalculating}
                  />
                  <p className="text-xs text-gray-500 mt-1">範圍: 90%-150%</p>
                </div>

                <div>
                  <Label htmlFor="knockin">保護價 (KI) %</Label>
                  <Input
                    id="knockin"
                    type="number"
                    placeholder="85"
                    value={knockInPrice}
                    onChange={(e) => setKnockInPrice(e.target.value)}
                    step="0.1"
                    min="50"
                    max="95"
                    disabled={isCalculating}
                  />
                  <p className="text-xs text-gray-500 mt-1">範圍: 50%-95% (必須低於轉換價)</p>
                </div>
              </div>

              {/* KI 類型選擇 */}
              <div>
                <Label htmlFor="kitype">保護價 (KI) 類型</Label>
                <Select value={kiType} onValueChange={setKiType} disabled={isCalculating}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="選擇保護價類型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EKI">EKI (歐式敲入)</SelectItem>
                    <SelectItem value="AKI">AKI (美式敲入)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  AKI 風險較高但收益率通常更優
                </p>
              </div>

              {/* 手續費收入設定 */}
              <div>
                <Label htmlFor="cost">手續費成本 (%)</Label>
                <Input
                  id="cost"
                  type="number"
                  placeholder="99.0"
                  value={cost}
                  onChange={(e) => setCost(e.target.value)}
                  step="0.1"
                  min="95"
                  max="99.8"
                  disabled={isCalculating}
                />
                <p className="text-xs text-gray-500 mt-1">
                  範圍: 95%-99.8% (99.0 = 1%手續費, 99.8 = 0.2%手續費)
                </p>
                <div className="text-xs text-blue-600 mt-1">
                  實際手續費收入: {cost ? (100 - parseFloat(cost)).toFixed(1) : '1.0'}%
                </div>
              </div>

              {/* 計算按鈕 */}
              <Button
                onClick={calculateFCN}
                disabled={isCalculating || selectedStocks.length === 0}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3"
                size="lg"
              >
                {isCalculating ? (
                  <>
                    <Clock className="h-5 w-5 mr-2 animate-spin" />
                    AI 模型計算中...
                  </>
                ) : (
                  <>
                    <Zap className="h-5 w-5 mr-2" />
                    開始 AI 智能試算
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* 右側結果展示區 */}
        <div className="space-y-6">
          {/* 計算結果卡片 */}
          <Card className="bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-gray-800">
                <TrendingUp className="h-5 w-5" />
                AI 智能試算結果
              </CardTitle>
              <CardDescription>
                {results ?
                  `使用 ${results.model_used} 模型計算結果` :
                  "設定參數後開始計算"
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              {results ? (
                <div className="space-y-6">
                  {/* 主要收益率展示 */}
                  <div className="flex justify-center">
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-100 p-8 rounded-lg border border-blue-200 w-72">
                      <div className="text-center">
                        <p className="text-5xl font-bold text-blue-600">
                          {results.annualized_yield.toFixed(2)}%
                        </p>
                        <p className="text-base text-blue-500 font-medium mt-3">預測年化收益率</p>
                        <p className="text-xs text-gray-500 mt-2">{results.model_used}</p>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* 詳細資訊 */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">連結股票</p>
                      <p className="font-medium">
                        {Object.keys(results.stock_info).join(', ')}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">承作期間</p>
                      <p className="font-medium">{results.input_params.tenure_months} 個月</p>
                    </div>
                    <div>
                      <p className="text-gray-600">閉鎖期</p>
                      <p className="font-medium">
                        {results.input_params.non_call_periods} 個月
                        {results.input_params.no_ko && (
                          <Badge variant="outline" className="ml-2 text-amber-600 border-amber-300">
                            不觸發KO
                          </Badge>
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">轉換價 (Strike)</p>
                      <p className="font-medium">{results.input_params.strike_pct}%</p>
                    </div>
                    <div>
                      <p className="text-gray-600">下限價 (KI)</p>
                      <p className="font-medium">{results.input_params.ki_barrier_pct}%</p>
                    </div>
                    <div>
                      <p className="text-gray-600">上限價 (KO)</p>
                      <p className="font-medium">
                        {results.input_params.ko_barrier_pct}%
                        {results.input_params.no_ko && (
                          <span className="text-gray-400 text-xs ml-1">(無效)</span>
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">KI 類型</p>
                      <p className="font-medium">{results.input_params.ki_type}</p>
                    </div>
                  </div>

                  {/* 市場參數資訊 */}
                  <div className="bg-gray-50 p-3 rounded text-xs text-gray-600">
                    <p className="font-semibold mb-2">市場參數 (來自每日數據)</p>
                    <div className="grid grid-cols-2 gap-2">
                      <p>SOFR利率: {results.market_params.SOFR_RATE?.toFixed(2)}%</p>
                      <p>VIX指數: {results.market_params.VIX_INDEX?.toFixed(2)}</p>
                    </div>
                  </div>

                  {/* 股票資訊 */}
                  <div className="bg-blue-50 p-3 rounded text-xs">
                    <p className="font-semibold mb-2 text-gray-700">連結股票詳情</p>
                    {Object.entries(results.stock_info).map(([symbol, info]: [string, any]) => (
                      <div key={symbol} className="mb-2 last:mb-0">
                        <p className="font-medium text-gray-800">{symbol}</p>
                        <div className="grid grid-cols-3 gap-2 text-gray-600">
                          <span>價格: ${info.price}</span>
                          <span>IV: {info.put_iv_3m?.toFixed(2)}%</span>
                          <span>Vol90D: {info.vol_90d?.toFixed(2)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Calculator className="h-16 w-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg mb-2">準備開始 FCN 試算</p>
                  <p className="text-sm">1. 選擇 1-3 檔股票</p>
                  <p className="text-sm">2. 設定 FCN 結構參數</p>
                  <p className="text-sm">3. 點擊計算獲得模型預測結果</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 風險提醒卡片 */}
          <Card className="bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
            <CardHeader>
              <CardTitle className="text-amber-800 text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                投資風險提醒
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-amber-700">
              <ul className="space-y-1">
                <li>• <strong>最差表現者風險：</strong>多檔股票組合的風險由表現最差的股票決定</li>
                <li>• <strong>敲入風險：</strong>若股價跌破敲入價，可能需承接股票或承擔損失</li>
                <li>• <strong>機會成本：</strong>若股價大幅上漲，收益將受敲出價限制</li>
                <li>• 本試算結果僅供參考，實際收益可能因市場變動而有差異</li>
                <li>• 請詳閱產品說明書並評估自身風險承受能力</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default FCNCalculatorV2;