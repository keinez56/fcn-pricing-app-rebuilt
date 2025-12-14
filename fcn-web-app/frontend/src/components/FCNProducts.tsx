
import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Calendar, DollarSign, TrendingUp, Users, Clock, Target } from 'lucide-react';
import { toast } from "@/hooks/use-toast";

const FCNProducts = () => {
  const [products] = useState([
    {
      id: 1,
      stocks: ['AAPL', 'MSFT', 'GOOGL'],
      K: 88.5,
      KO: 105.2,
      KI: 70.8,
      yield: 22.5,
      deadline: '2025-07-15',
      targetAmount: 300000,
      currentAmount: 450000,
      participants: 8,
      minInvestment: 10000,
      description: '科技股三強組合',
      hot: true
    },
    {
      id: 2,
      stocks: ['TSLA', 'NVDA'],
      K: 92.0,
      KO: 108.5,
      KI: 75.2,
      yield: 28.8,
      deadline: '2025-07-20',
      targetAmount: 300000,
      currentAmount: 380000,
      participants: 7,
      minInvestment: 10000,
      description: '電動車 × AI 概念',
      hot: true
    },
    {
      id: 3,
      stocks: ['JPM', 'BAC', 'WFC'],
      K: 82.3,
      KO: 102.8,
      KI: 65.5,
      yield: 18.2,
      deadline: '2025-07-25',
      targetAmount: 300000,
      currentAmount: 320000,
      participants: 6,
      minInvestment: 10000,
      description: '金融股穩健組合',
      hot: false
    },
    {
      id: 4,
      stocks: ['AMZN', 'META'],
      K: 90.8,
      KO: 110.5,
      KI: 72.0,
      yield: 25.6,
      deadline: '2025-07-30',
      targetAmount: 300000,
      currentAmount: 290000,
      participants: 5,
      minInvestment: 10000,
      description: '網路巨頭雙星',
      hot: false
    },
    {
      id: 5,
      stocks: ['PFE', 'JNJ', 'UNH'],
      K: 85.2,
      KO: 104.8,
      KI: 68.5,
      yield: 20.1,
      deadline: '2025-08-05',
      targetAmount: 300000,
      currentAmount: 410000,
      participants: 9,
      minInvestment: 10000,
      description: '醫療保健防禦型',
      hot: false
    }
  ]);

  const handleSubscribe = (productId: number, productName: string) => {
    toast({
      title: "跟單申請",
      description: `已收到您對「${productName}」的跟單申請，專員將盡快與您聯繫`,
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const calculateProgress = (current: number, target: number) => {
    return Math.min((current / target) * 100, 100);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  return (
    <div className="space-y-6">
      {/* 頁面標題 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">FCN 募集中商品</h2>
        <p className="text-gray-600">目前正在募集的 FCN 商品，歡迎跟單參與</p>
      </div>

      {/* 產品列表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {products.map((product) => (
          <Card key={product.id} className={`relative overflow-hidden transition-all hover:shadow-lg ${product.hot ? 'ring-2 ring-orange-200' : ''}`}>
            {product.hot && (
              <div className="absolute top-0 right-0 bg-gradient-to-l from-orange-500 to-red-500 text-white px-3 py-1 text-xs font-bold">
                🔥 熱門
              </div>
            )}
            
            <CardHeader className="pb-4">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-blue-600" />
                    {product.description}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {product.stocks.join(' + ')}
                  </CardDescription>
                </div>
                <Badge variant={product.currentAmount >= product.targetAmount ? "default" : "secondary"} className="ml-2">
                  {product.currentAmount >= product.targetAmount ? "募集達標" : "募集中"}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* FCN 參數 */}
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="text-center p-2 bg-gray-50 rounded">
                  <p className="text-xs text-gray-500">轉換價 K</p>
                  <p className="font-bold text-gray-800">${product.K}</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded">
                  <p className="text-xs text-gray-500">上限 KO</p>
                  <p className="font-bold text-blue-600">${product.KO}</p>
                </div>
                <div className="text-center p-2 bg-red-50 rounded">
                  <p className="text-xs text-gray-500">下限 KI</p>
                  <p className="font-bold text-red-600">${product.KI}</p>
                </div>
              </div>

              {/* 收益率 */}
              <div className="text-center p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg">
                <p className="text-sm text-gray-600">預期年化收益率</p>
                <p className="text-2xl font-bold text-green-600">{product.yield}%</p>
              </div>

              {/* 募集進度 */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">募集進度</span>
                  <span className="font-medium">
                    {formatCurrency(product.currentAmount)} / {formatCurrency(product.targetAmount)}
                  </span>
                </div>
                <Progress 
                  value={calculateProgress(product.currentAmount, product.targetAmount)} 
                  className="h-2"
                />
                <div className="flex justify-between items-center text-xs text-gray-500">
                  <span>{calculateProgress(product.currentAmount, product.targetAmount).toFixed(1)}% 完成</span>
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {product.participants} 人參與
                  </span>
                </div>
              </div>

              {/* 重要資訊 */}
              <div className="grid grid-cols-2 gap-3 text-xs text-gray-600">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  截止: {formatDate(product.deadline)}
                </div>
                <div className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3" />
                  最低: {formatCurrency(product.minInvestment)}
                </div>
              </div>

              {/* 跟單按鈕 */}
              <Button 
                onClick={() => handleSubscribe(product.id, product.description)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                disabled={new Date(product.deadline) < new Date()}
              >
                {new Date(product.deadline) < new Date() ? '募集已截止' : '我要跟單'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 常見問題與風險說明 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-blue-800 text-lg">常見問題</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-blue-700 space-y-2">
            <div>
              <p className="font-medium">Q: 什麼是 FCN？</p>
              <p>A: Fixed Coupon Note，固定票息票券，提供穩定收益的結構性商品。</p>
            </div>
            <div>
              <p className="font-medium">Q: 如何計算收益？</p>
              <p>A: 依據連結標的表現與票券條款，在到期時結算本金與利息。</p>
            </div>
            <div>
              <p className="font-medium">Q: 最低投資門檻？</p>
              <p>A: 美股 FCN 最低投資金額為 $10,000 美元。</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-yellow-50 border-yellow-200">
          <CardHeader>
            <CardTitle className="text-yellow-800 text-lg">風險說明</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-yellow-700 space-y-2">
            <p>• <strong>市場風險：</strong>連結標的價格波動可能影響本金安全</p>
            <p>• <strong>匯率風險：</strong>美股 FCN 涉及美元匯率變動風險</p>
            <p>• <strong>信用風險：</strong>發行機構信用狀況可能影響償付能力</p>
            <p>• <strong>流動性風險：</strong>到期前可能無法提前贖回</p>
            <p className="text-xs mt-2 text-gray-600">
              ※ 投資前請詳閱公開說明書，本資料僅供參考
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FCNProducts;
