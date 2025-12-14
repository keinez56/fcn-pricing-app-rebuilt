
import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Copy, Package, Calendar } from 'lucide-react';
import { toast } from "@/hooks/use-toast";

interface FCNCombo {
  id: string;
  name: string;
  stocks: string[];
  K: number;
  KO: number;
  KI: number;
  period: number;
  yield: number;
  description: string;
  validUntil: string;
}

const FCNRecommendations = () => {
  const [activeCategory, setActiveCategory] = useState<'conservative' | 'aggressive' | 'short'>('conservative');

  const combinations = {
    conservative: [
      {
        id: '1',
        name: '大型科技穩健型',
        stocks: ['AAPL', 'MSFT', 'GOOGL'],
        K: 85,
        KO: 110,
        KI: 70,
        period: 6,
        yield: 12.5,
        description: '科技巨頭穩健收益組合',
        validUntil: '2025/07/05'
      },
      {
        id: '2', 
        name: '多元化藍籌股',
        stocks: ['JNJ', 'PG', 'KO'],
        K: 75,
        KO: 105,
        KI: 60,
        period: 9,
        yield: 15.2,
        description: '傳統藍籌股穩定組合',
        validUntil: '2025/07/10'
      },
      {
        id: '3',
        name: '金融服務型',
        stocks: ['JPM', 'BAC', 'WFC'],
        K: 80,
        KO: 115,
        KI: 65,
        period: 12,
        yield: 18.0,
        description: '美國大型銀行組合',
        validUntil: '2025/07/15'
      }
    ],
    aggressive: [
      {
        id: '4',
        name: '高成長科技型',
        stocks: ['TSLA', 'NVDA', 'AMD'],
        K: 90,
        KO: 120,
        KI: 75,
        period: 6,
        yield: 25.5,
        description: '高成長潛力科技股',
        validUntil: '2025/07/08'
      },
      {
        id: '5',
        name: '生技創新型',
        stocks: ['PFE', 'MRNA'],
        K: 70,
        KO: 108,
        KI: 55,
        period: 8,
        yield: 28.2,
        description: '生技醫療高報酬組合',
        validUntil: '2025/07/12'
      },
      {
        id: '6',
        name: '新興產業型',
        stocks: ['PLTR', 'SNOW', 'CRWD'],
        K: 95,
        KO: 118,
        KI: 80,
        period: 10,
        yield: 32.0,
        description: '新興科技潛力股',
        validUntil: '2025/07/20'
      }
    ],
    short: [
      {
        id: '7',
        name: '短線價差型',
        stocks: ['SPY', 'QQQ'],
        K: 88,
        KO: 112,
        KI: 72,
        period: 3,
        yield: 19.8,
        description: 'ETF短期波段操作組合',
        validUntil: '2025/07/03'
      },
      {
        id: '8',
        name: '高頻交易型',
        stocks: ['AMZN', 'META'],
        K: 82,
        KO: 106,
        KI: 68,
        period: 2,
        yield: 21.5,
        description: '超短線高頻策略',
        validUntil: '2025/07/01'
      },
      {
        id: '9',
        name: '事件驅動型',
        stocks: ['NFLX', 'DIS', 'UBER'],
        K: 77,
        KO: 103,
        KI: 62,
        period: 4,
        yield: 24.2,
        description: '基於事件驅動的短線組合',
        validUntil: '2025/07/06'
      }
    ]
  };

  const copyComboParams = (combo: FCNCombo) => {
    const params = `美股: ${combo.stocks.join(', ')}
轉換價(K): $${combo.K}
上限價格(KO): $${combo.KO}  
下限價格(KI): $${combo.KI}
承作期間: ${combo.period}個月
預估年化收益率: ${combo.yield}%`;

    navigator.clipboard.writeText(params);
    
    toast({
      title: "已複製參數",
      description: `${combo.name} 的參數已複製到剪貼簿`
    });
  };

  const categories = {
    conservative: { name: '穩健派', color: 'bg-green-100 text-green-800 border-green-200' },
    aggressive: { name: '積極型', color: 'bg-red-100 text-red-800 border-red-200' },
    short: { name: '短打型', color: 'bg-blue-100 text-blue-800 border-blue-200' }
  };

  return (
    <div className="space-y-6">
      {/* 分類選擇 */}
      <div className="flex justify-center">
        <div className="flex space-x-2 p-1 bg-gray-100 rounded-lg">
          {Object.entries(categories).map(([key, category]) => (
            <Button
              key={key}
              variant={activeCategory === key ? "default" : "ghost"}
              onClick={() => setActiveCategory(key as any)}
              className={`px-6 ${activeCategory === key ? 'bg-blue-600 text-white' : 'text-gray-600'}`}
            >
              {category.name}
            </Button>
          ))}
        </div>
      </div>

      {/* 組合卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {combinations[activeCategory].map((combo) => (
          <Card key={combo.id} className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg font-bold text-gray-800">
                    {combo.name}
                  </CardTitle>
                  <CardDescription className="text-sm text-gray-600 mt-1">
                    {combo.description}
                  </CardDescription>
                </div>
                <Badge className={`${categories[activeCategory].color} text-xs`}>
                  {categories[activeCategory].name}
                </Badge>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* 股票代碼 */}
              <div>
                <p className="text-sm text-gray-600 mb-1">連結美股</p>
                <div className="flex flex-wrap gap-1">
                  {combo.stocks.map((stock) => (
                    <Badge key={stock} variant="outline" className="text-xs">
                      {stock}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 參數資訊 */}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-gray-600">K / KO / KI</p>
                  <p className="font-semibold">${combo.K} / ${combo.KO} / ${combo.KI}</p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-gray-600">期間</p>
                  <p className="font-semibold">{combo.period} 個月</p>
                </div>
              </div>

              {/* 預估收益率 */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 rounded-lg text-center">
                <p className="text-sm text-gray-600">預估年化收益率</p>
                <p className="text-2xl font-bold text-blue-600">{combo.yield}%</p>
              </div>

              {/* 有效期限 */}
              <div className="flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  建議有效期至
                </div>
                <span>{combo.validUntil}</span>
              </div>

              {/* 複製按鈕 */}
              <Button
                onClick={() => copyComboParams(combo)}
                variant="outline"
                className="w-full border-blue-300 text-blue-600 hover:bg-blue-50"
              >
                <Copy className="h-4 w-4 mr-2" />
                複製此組合參數
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 底部說明 */}
      <Card className="bg-gradient-to-r from-yellow-50 to-amber-50 border-yellow-200">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Package className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-700">
              <p className="font-semibold mb-1">使用說明</p>
              <ul className="space-y-1 text-xs">
                <li>• 組合參數僅供參考，實際承作前請確認美股市價</li>
                <li>• 建議有效期限會根據市場狀況調整</li>
                <li>• 複製參數後可直接在詢價試算頁面使用</li>
                <li>• 所有收益率為預估值，實際報酬可能有差異</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default FCNRecommendations;
