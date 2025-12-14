
import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { TrendingUp, AlertCircle, CheckCircle2, Minus } from 'lucide-react';
import { toast } from "@/hooks/use-toast";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const FCNAnalysis = () => {
  const [stock1, setStock1] = useState<string>('');
  const [stock2, setStock2] = useState<string>('');
  const [stock3, setStock3] = useState<string>('');
  const [vol1, setVol1] = useState<string>('25');
  const [vol2, setVol2] = useState<string>('30');
  const [vol3, setVol3] = useState<string>('28');
  const [marketVol, setMarketVol] = useState<string>('20');
  const [sentiment, setSentiment] = useState<string>('50');
  const [priceLevel, setPriceLevel] = useState<string>('50');
  const [analysis, setAnalysis] = useState<any>(null);

  const generateAnalysis = () => {
    if (!stock1) {
      toast({
        title: "錯誤",
        description: "請至少填寫第一檔美股代碼",
        variant: "destructive"
      });
      return;
    }

    // 分數計算邏輯
    let totalScore = 0;
    
    // 1. 波動率評分 (0-40分) - 波動率越高加分越多
    const marketVolValue = parseFloat(marketVol);
    const avgIndividualVol = (parseFloat(vol1) + (vol2 ? parseFloat(vol2) : 0) + (vol3 ? parseFloat(vol3) : 0)) / (vol2 && vol3 ? 3 : vol2 ? 2 : 1);
    const avgVol = (marketVolValue + avgIndividualVol) / 2;
    
    let volScore = 0;
    if (avgVol >= 35) volScore = 40;
    else if (avgVol >= 30) volScore = 35;
    else if (avgVol >= 25) volScore = 30;
    else if (avgVol >= 20) volScore = 20;
    else volScore = 10;
    
    // 2. 市場情緒評分 (0-30分) - 情緒指標越低加分越多（反向指標）
    const sentValue = parseFloat(sentiment);
    let sentScore = 0;
    if (sentValue <= 20) sentScore = 30;
    else if (sentValue <= 40) sentScore = 25;
    else if (sentValue <= 60) sentScore = 15;
    else if (sentValue <= 80) sentScore = 10;
    else sentScore = 5;
    
    // 3. 股價位階評分 (0-30分) - 位階越低加分越多
    const levelValue = parseFloat(priceLevel);
    let levelScore = 0;
    if (levelValue <= 20) levelScore = 30;
    else if (levelValue <= 40) levelScore = 25;
    else if (levelValue <= 60) levelScore = 15;
    else if (levelValue <= 80) levelScore = 10;
    else levelScore = 5;
    
    totalScore = volScore + sentScore + levelScore;
    
    // 根據總分決定建議
    let recommendation = "";
    let icon = "";
    let yieldRange = "";
    let periodRange = "";
    let description = "";
    let suggestedK = 70 + Math.random() * 25; // 70-95
    
    if (totalScore >= 75) {
      recommendation = "👍 適合投資 FCN";
      icon = "🟢";
      yieldRange = "20-35%";
      periodRange = "6-12 個月";
      description = "可爭取較高年化殖利率，建議要求 >20%";
    } else if (totalScore >= 45) {
      recommendation = "⚖️ 市場觀望中";
      icon = "🟡";
      yieldRange = "15-25%";
      periodRange = "3-6 個月";
      description = "應審慎估價，殖利率建議在中間值區間";
    } else {
      recommendation = "❌ 目前不建議承作 FCN";
      icon = "🔴";
      yieldRange = "10-20%";
      periodRange = "1-3 個月";
      description = "建議等市場波動擴大或位階降低再承作";
    }

    // 準備雷達圖數據
    const radarData = [
      {
        subject: '波動率環境',
        score: (volScore / 40) * 100,
        fullMark: 100
      },
      {
        subject: '市場情緒',
        score: (sentScore / 30) * 100,
        fullMark: 100
      },
      {
        subject: '股價位階',
        score: (levelScore / 30) * 100,
        fullMark: 100
      }
    ];

    // 準備圓餅圖數據
    const pieData = [
      { name: '適合度', value: totalScore },
      { name: '風險度', value: 100 - totalScore }
    ];

    setAnalysis({
      totalScore,
      recommendation,
      icon,
      yieldRange,
      periodRange,
      description,
      suggestedK: suggestedK.toFixed(1),
      radarData,
      pieData,
      factors: {
        volatility: avgVol.toFixed(1),
        sentiment: sentValue,
        priceLevel: levelValue,
        volScore,
        sentScore,
        levelScore
      }
    });

    toast({
      title: "分析完成",
      description: `投資建議: ${recommendation.replace(/[👍⚖️❌]/g, '').trim()}`
    });
  };

  const COLORS = ['#84C1FF', '#FF8884'];

  const chartConfig = {
    score: {
      label: "分數",
    },
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 左側輸入區 */}
      <Card className="bg-white shadow-lg">
        <CardHeader className="bg-gradient-to-r from-blue-400 to-blue-600 text-white">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            FCN 投資時機分析
          </CardTitle>
          <CardDescription className="text-blue-100">
            輸入美股市場資訊以評估投資時機
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          <div className="space-y-4">
            <Label className="text-sm font-medium text-gray-700">美股代碼與個股波動率 (%)</Label>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="第一檔 (如: AAPL)"
                value={stock1}
                onChange={(e) => setStock1(e.target.value)}
              />
              <Input
                type="number"
                placeholder="波動率 %"
                value={vol1}
                onChange={(e) => setVol1(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="第二檔 (如: TSLA)"
                value={stock2}
                onChange={(e) => setStock2(e.target.value)}
              />
              <Input
                type="number"
                placeholder="波動率 %"
                value={vol2}
                onChange={(e) => setVol2(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="第三檔 (如: NVDA)"
                value={stock3}
                onChange={(e) => setStock3(e.target.value)}
              />
              <Input
                type="number"
                placeholder="波動率 %"
                value={vol3}
                onChange={(e) => setVol3(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="marketVol">大盤波動率 (%)</Label>
              <Input
                id="marketVol"
                type="number"
                value={marketVol}
                onChange={(e) => setMarketVol(e.target.value)}
              />
            </div>
            
            <div>
              <Label htmlFor="sentiment">市場情緒指標 (0-100)</Label>
              <Input
                id="sentiment"
                type="number"
                placeholder="0=極度悲觀, 100=極度樂觀"
                value={sentiment}
                onChange={(e) => setSentiment(e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="priceLevel">股價相對位階 (0-100%)</Label>
              <Input
                id="priceLevel"
                type="number"
                placeholder="0%=年內最低, 100%=年內最高"
                value={priceLevel}
                onChange={(e) => setPriceLevel(e.target.value)}
              />
            </div>
          </div>

          <Button 
            onClick={generateAnalysis}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3"
            size="lg"
          >
            產出建議
          </Button>
        </CardContent>
      </Card>

      {/* 右側結果區 */}
      <div className="space-y-6">
        <Card className="bg-white shadow-lg">
          <CardHeader>
            <CardTitle className="text-gray-800">投資時機分析結果</CardTitle>
            <CardDescription>
              基於市場環境的綜合評估建議
            </CardDescription>
          </CardHeader>
          <CardContent>
            {analysis ? (
              <div className="space-y-6">
                {/* 主要建議結果 */}
                <div className="text-center p-6 bg-gradient-to-r from-blue-50 to-slate-50 rounded-lg">
                  <div className="text-4xl mb-2">{analysis.icon}</div>
                  <p className="text-2xl font-bold text-gray-800 mb-2">
                    {analysis.recommendation}
                  </p>
                  <p className="text-lg text-gray-600 mb-1">
                    {analysis.description}
                  </p>
                  <p className="text-sm text-gray-500">
                    綜合評分: {analysis.totalScore}/100
                  </p>
                </div>

                {/* 推薦參數 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-2">建議殖利率區間</h4>
                    <p className="text-xl font-bold text-blue-600">
                      {analysis.yieldRange}
                    </p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-2">建議承作期間</h4>
                    <p className="text-xl font-bold text-green-600">
                      {analysis.periodRange}
                    </p>
                  </div>
                </div>

                {/* FCN 建議參數 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-semibold text-gray-800 mb-2">FCN 參考參數</h4>
                  <div className="text-sm text-gray-600">
                    <p>建議轉換價 (K): ${analysis.suggestedK}</p>
                  </div>
                </div>

                {/* 雷達圖 */}
                <div className="bg-white border rounded-lg p-4">
                  <h4 className="font-semibold text-gray-800 mb-4 text-center">市場條件分析</h4>
                  <ChartContainer config={chartConfig} className="h-64">
                    <RadarChart data={analysis.radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="subject" className="text-xs" />
                      <Radar
                        name="分數"
                        dataKey="score"
                        stroke="#84C1FF"
                        fill="#84C1FF"
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                      <ChartTooltip content={<ChartTooltipContent />} />
                    </RadarChart>
                  </ChartContainer>
                </div>

                {/* 各項指標詳情 */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-gray-800">各項指標評分</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span>波動率環境 ({analysis.factors.volatility}%)</span>
                      <span className="font-bold text-blue-600">
                        {analysis.factors.volScore}/40
                      </span>
                    </div>
                    <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span>市場情緒 ({analysis.factors.sentiment})</span>
                      <span className="font-bold text-blue-600">
                        {analysis.factors.sentScore}/30
                      </span>
                    </div>
                    <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span>股價位階 ({analysis.factors.priceLevel}%)</span>
                      <span className="font-bold text-blue-600">
                        {analysis.factors.levelScore}/30
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>請填寫市場參數並點擊「產出建議」</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200">
          <CardHeader>
            <CardTitle className="text-orange-800 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              重要提醒
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-orange-700">
            <ul className="space-y-1">
              <li>• 建議值為模擬估算，實際仍應由專業理專提供報價</li>
              <li>• 市場波動加劇時 FCN 產品設計較有利</li>
              <li>• 股價位階過高時需謹慎評估敲入風險</li>
              <li>• 市場情緒極度樂觀時建議保守操作</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FCNAnalysis;
