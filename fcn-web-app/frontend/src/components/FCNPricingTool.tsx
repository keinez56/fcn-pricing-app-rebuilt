import React, { useState, useCallback } from 'react';
import { Calculator, RotateCcw, Info, TrendingUp, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { TickerInput } from './TickerInput';
import { ParameterSlider } from './ParameterSlider';
import { QuoteSummary } from './QuoteSummary';
import { ThemeToggle } from './ThemeToggle';
import { IVDataUpload } from './IVDataUpload';
import { FCNParameters, defaultFCNParameters, calculateQuote } from '@/lib/fcn-calculations';
import { toast } from '@/hooks/use-toast';

export function FCNPricingTool() {
  const [params, setParams] = useState<FCNParameters>(defaultFCNParameters);
  const [quote, setQuote] = useState(() => calculateQuote(defaultFCNParameters));
  const [isCalculating, setIsCalculating] = useState(false);

  // Validation: KI must be less than Strike
  const kiError = params.knockInBarrier >= params.strikePrice
    ? '敲入價必須低於履約價'
    : undefined;

  const updateParam = useCallback(<K extends keyof FCNParameters>(
    key: K,
    value: FCNParameters[K]
  ) => {
    setParams(prev => {
      const newParams = { ...prev, [key]: value };

      // Auto-adjust KI if it would exceed Strike
      if (key === 'strikePrice' && typeof value === 'number') {
        if (prev.knockInBarrier >= value) {
          newParams.knockInBarrier = value - 5;
        }
      }

      // Auto-adjust protection period if it would exceed tenor
      if (key === 'tenor' && typeof value === 'number') {
        if (prev.protectionPeriod > value) {
          newParams.protectionPeriod = value;
        }
      }

      return newParams;
    });
  }, []);

  const handleCalculate = useCallback(() => {
    if (kiError) {
      toast({
        title: "驗證錯誤",
        description: kiError,
        variant: "destructive",
      });
      return;
    }

    if (params.underlyingAssets.length === 0) {
      toast({
        title: "驗證錯誤",
        description: "請至少新增一個標的資產",
        variant: "destructive",
      });
      return;
    }

    setIsCalculating(true);

    // Simulate calculation delay
    setTimeout(() => {
      const newQuote = calculateQuote(params);
      setQuote(newQuote);
      setIsCalculating(false);

      toast({
        title: "報價計算完成",
        description: `參考年化票息: ${newQuote.annualizedCoupon.toFixed(2)}% p.a.`,
      });
    }, 500);
  }, [params, kiError]);

  const handleReset = useCallback(() => {
    setParams(defaultFCNParameters);
    setQuote(calculateQuote(defaultFCNParameters));
    toast({
      title: "重置完成",
      description: "所有參數已恢復為預設值",
    });
  }, []);

  return (
    <div className="min-h-screen bg-background p-4 lg:p-8">
      {/* Header */}
      <header className="mb-8 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <TrendingUp className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
                FCN 詢價工具
              </h1>
              <p className="text-sm text-muted-foreground">
                固定票息票據報價與模擬
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <IVDataUpload />
            <Link to="/ai-smart-quote">
              <Button variant="outline" className="gap-2">
                <Sparkles className="h-4 w-4" />
                <span className="hidden sm:inline">AI 智慧詢價</span>
              </Button>
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Left Panel - Parameters */}
        <Card className="card-gradient border-border/50 animate-fade-in">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calculator className="h-5 w-5 text-primary" />
              FCN 參數設定
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Underlying Assets */}
            <TickerInput
              tickers={params.underlyingAssets}
              onChange={(tickers) => updateParam('underlyingAssets', tickers)}
              maxTickers={4}
            />

            {/* Strike Price */}
            <ParameterSlider
              label="履約價"
              value={params.strikePrice}
              onChange={(v) => updateParam('strikePrice', v)}
              min={50}
              max={100}
              tooltip="用於決定贖回金額的初始股價百分比。履約價越低 = 保護越多但票息越低。"
            />

            {/* Knock-Out Barrier */}
            <ParameterSlider
              label="敲出價 (KO)"
              value={params.knockOutBarrier}
              onChange={(v) => updateParam('knockOutBarrier', v)}
              min={90}
              max={150}
              tooltip="若股價上漲超過此水平，票據將提前終止並返還全部本金。敲出價越高 = 觸發機率越低。"
            />

            {/* Knock-In Barrier */}
            <ParameterSlider
              label="敲入價 (KI)"
              value={params.knockInBarrier}
              onChange={(v) => updateParam('knockInBarrier', v)}
              min={50}
              max={Math.min(90, params.strikePrice - 1)}
              tooltip="若股價跌破此水平，到期時可能收到股票而非現金。敲入價越低 = 保護越多。"
              error={kiError}
            />

            {/* Barrier Type */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">障礙類型</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p><strong>EKI (歐式):</strong> 僅於到期日觀察障礙 - 風險較低。</p>
                    <p className="mt-1"><strong>AKI (美式):</strong> 於存續期間持續觀察障礙 - 票息較高但風險較高。</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <RadioGroup
                value={params.barrierType}
                onValueChange={(v) => updateParam('barrierType', v as 'EKI' | 'AKI')}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="EKI" id="eki" />
                  <Label htmlFor="eki" className="cursor-pointer font-mono text-sm">
                    EKI (歐式)
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="AKI" id="aki" />
                  <Label htmlFor="aki" className="cursor-pointer font-mono text-sm">
                    AKI (美式)
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Issue Price */}
            <ParameterSlider
              label="發行價格 / 成本"
              value={params.issuePrice}
              onChange={(v) => updateParam('issuePrice', v)}
              min={95}
              max={100}
              tooltip="您預付的名目金額百分比。發行價格越低 = 購買折扣越多。"
            />

            {/* Tenor */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">存續期間(月)</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>票據至到期日的期間。</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <Select
                value={params.tenor.toString()}
                onValueChange={(v) => updateParam('tenor', parseInt(v))}
              >
                <SelectTrigger className="bg-muted/50 border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(m => (
                    <SelectItem key={m} value={m.toString()}>
                      {m} 個月
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Protection Period */}
            <ParameterSlider
              label="保息期間(月)"
              value={params.protectionPeriod}
              onChange={(v) => updateParam('protectionPeriod', v)}
              min={1}
              max={params.tenor}
              unit="月"
              tooltip="在此期間內，無論是否觸發敲出，都將保證獲得票息。最低1個月，最高等於存續期間。"
            />

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleCalculate}
                disabled={isCalculating || !!kiError}
                className="flex-1 h-12 text-base font-medium glow-primary"
              >
                {isCalculating ? (
                  <span className="flex items-center gap-2">
                    <div className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    計算中...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Calculator className="h-5 w-5" />
                    計算報價
                  </span>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={handleReset}
                className="h-12 px-6"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                重置
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Right Panel - Results */}
        <div className="space-y-6 animate-slide-in-right">
          <QuoteSummary params={params} quote={quote} />
        </div>
      </div>

      {/* Footer Disclaimer */}
      <footer className="mt-8 text-center text-xs text-muted-foreground animate-fade-in">
        <p>
          本工具僅提供參考報價，僅供說明用途。
          實際條款可能因市場狀況而異。
          在做出投資決策前，請諮詢財務顧問。
        </p>
      </footer>
    </div>
  );
}
