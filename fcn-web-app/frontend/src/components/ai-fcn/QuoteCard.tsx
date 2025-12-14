import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, Shield, AlertTriangle } from 'lucide-react';
import { type FCNQuote, getStockColor, getStockName } from '@/lib/ai-fcn-utils';

interface QuoteCardProps {
  quote: FCNQuote;
  index: number;
  isTopPick?: boolean;
}

export function QuoteCard({ quote, index, isTopPick }: QuoteCardProps) {
  const riskConfig = {
    low: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: Shield, label: '低風險' },
    medium: { color: 'text-amber-600', bg: 'bg-amber-50', icon: TrendingUp, label: '中風險' },
    high: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle, label: '高風險' },
  };

  const risk = riskConfig[quote.riskLevel];
  const RiskIcon = risk.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.3 }}
    >
      <Card className={`
        overflow-hidden transition-all hover:shadow-lg hover:scale-[1.02] cursor-pointer
        ${isTopPick ? 'ring-2 ring-blue-500 shadow-blue-100' : ''}
      `}>
        <CardContent className="p-4 space-y-3">
          {/* 排名標籤 */}
          {isTopPick && (
            <div className="absolute top-2 right-2">
              <Badge className="bg-gradient-to-r from-amber-400 to-amber-600 text-white">
                #{index + 1}
              </Badge>
            </div>
          )}

          {/* 股票標籤 */}
          <div className="flex items-center gap-1 flex-wrap">
            {quote.stocks.map((symbol) => {
              const color = getStockColor(symbol);
              return (
                <Badge
                  key={symbol}
                  variant="outline"
                  className="text-xs font-mono"
                  style={{
                    borderColor: color,
                    color: color,
                    backgroundColor: `${color}15`
                  }}
                  title={getStockName(symbol)}
                >
                  {symbol}
                </Badge>
              );
            })}
            <Badge variant="secondary" className="text-xs ml-auto">
              {quote.basketSize} 檔
            </Badge>
          </div>

          {/* Coupon 率 */}
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${quote.couponRate >= 15 ? 'text-emerald-600' : quote.couponRate >= 10 ? 'text-blue-600' : 'text-gray-700'}`}>
              {quote.couponRate.toFixed(2)}%
            </span>
            <span className="text-xs text-gray-500">年化票息</span>
            {quote.yieldBoost !== null && quote.yieldBoost > 0 && (
              <Badge className="bg-emerald-100 text-emerald-700 text-xs">
                +{quote.yieldBoost.toFixed(1)}%
              </Badge>
            )}
          </div>

          {/* 統計資訊 */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-1">
              <span className="text-gray-500">距KI:</span>
              <span className="font-medium">{quote.distanceToKI.toFixed(1)}%</span>
            </div>
            {quote.maxIV && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500">最高IV:</span>
                <span className="font-medium">{quote.maxIV.toFixed(1)}%</span>
              </div>
            )}
          </div>

          {/* 風險等級 */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs w-fit ${risk.bg}`}>
            <RiskIcon className={`h-3.5 w-3.5 ${risk.color}`} />
            <span className={risk.color}>{risk.label}</span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
