import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Area, ComposedChart } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';
import { FCNParameters, generatePayoffData, calculateQuote } from '@/lib/fcn-calculations';

interface PayoffChartProps {
  params: FCNParameters;
}

export function PayoffChart({ params }: PayoffChartProps) {
  const quote = calculateQuote(params);
  const couponReturn = quote.bestCaseReturn;
  const data = generatePayoffData(params, couponReturn);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-xs text-muted-foreground mb-1">股票表現</p>
          <p className="font-mono font-medium text-foreground">{label}%</p>
          <p className="text-xs text-muted-foreground mt-2 mb-1">贖回金額</p>
          <p className="font-mono font-medium text-primary">{payload[0].value.toFixed(1)}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="card-gradient border-border/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <TrendingUp className="h-5 w-5 text-primary" />
          到期收益圖
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
              <defs>
                <linearGradient id="payoffGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(199, 89%, 48%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(199, 89%, 48%)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
              <XAxis
                dataKey="stockPerformance"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                label={{
                  value: '股票表現 (%)',
                  position: 'bottom',
                  offset: 0,
                  fill: 'hsl(var(--muted-foreground))',
                  fontSize: 11
                }}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                domain={[0, Math.ceil((110 + couponReturn) / 10) * 10]}
                label={{
                  value: '贖回金額 (%)',
                  angle: -90,
                  position: 'insideLeft',
                  fill: 'hsl(var(--muted-foreground))',
                  fontSize: 11
                }}
              />
              <Tooltip content={<CustomTooltip />} />

              {/* Reference Lines */}
              <ReferenceLine
                x={params.strikePrice}
                stroke="hsl(38, 92%, 50%)"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: `履約價 ${params.strikePrice}%`,
                  position: 'top',
                  fill: 'hsl(38, 92%, 50%)',
                  fontSize: 10
                }}
              />
              <ReferenceLine
                x={params.knockInBarrier}
                stroke="hsl(0, 72%, 51%)"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: `敲入 ${params.knockInBarrier}%`,
                  position: 'top',
                  fill: 'hsl(0, 72%, 51%)',
                  fontSize: 10
                }}
              />
              <ReferenceLine
                x={params.knockOutBarrier}
                stroke="hsl(142, 76%, 36%)"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: `敲出 ${params.knockOutBarrier}%`,
                  position: 'top',
                  fill: 'hsl(142, 76%, 36%)',
                  fontSize: 10
                }}
              />
              <ReferenceLine
                y={100}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="3 3"
              />

              <Area
                type="monotone"
                dataKey="redemptionAmount"
                stroke="transparent"
                fill="url(#payoffGradient)"
              />
              <Line
                type="monotone"
                dataKey="redemptionAmount"
                stroke="hsl(199, 89%, 48%)"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6, fill: 'hsl(199, 89%, 48%)', stroke: 'hsl(var(--background))', strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap justify-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-[hsl(38,92%,50%)]" />
            <span className="text-muted-foreground">履約價</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-destructive" />
            <span className="text-muted-foreground">敲入價</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-accent" />
            <span className="text-muted-foreground">敲出價</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
