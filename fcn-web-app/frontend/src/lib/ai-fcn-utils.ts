// AI FCN 智慧詢價工具函數

export interface Stock {
  code: string;
  name: string;
  price: number | null;
  vol90d: number | null;
  iv: number | null;
  color: string;
}

export interface AIFCNParams {
  selectedStocks: string[];
  basketSizes: number[];
  strikePrice: number;
  knockIn: number;
  knockOut: number;
  tenor: number;
  nonCallPeriods: number;
  kiType: string;
  cost: number;
}

export interface FCNQuote {
  id: string;
  stocks: string[];
  basketSize: number;
  couponRate: number;
  distanceToKI: number;
  maxIV: number | null;
  yieldBoost: number | null;
  riskLevel: "low" | "medium" | "high";
  stockInfo: Record<string, {
    price: number | null;
    put_iv_3m: number | null;
    vol_90d: number | null;
  }>;
}

export interface BatchQuoteResponse {
  quotes: FCNQuote[];
  totalCount: number;
  pricingDate: string;
  params: {
    period: number;
    strikePrice: number;
    knockOutPrice: number;
    knockInPrice: number;
    kiType: string;
    nonCallPeriods: number;
    noKO: boolean;
  };
  marketParams: {
    SOFR_RATE: number;
    VIX_INDEX: number;
  };
}

// 股票顏色映射
const STOCK_COLORS: Record<string, string> = {
  'TSM': 'hsl(210, 80%, 50%)',
  'NVDA': 'hsl(120, 70%, 40%)',
  'GOOGL': 'hsl(45, 90%, 50%)',
  'GOOG': 'hsl(45, 90%, 50%)',
  'AAPL': 'hsl(0, 0%, 50%)',
  'MSFT': 'hsl(200, 80%, 50%)',
  'AMZN': 'hsl(30, 90%, 50%)',
  'INTC': 'hsl(210, 90%, 60%)',
  'AMD': 'hsl(0, 70%, 50%)',
  'META': 'hsl(220, 80%, 55%)',
  'TSLA': 'hsl(0, 80%, 55%)',
  'BABA': 'hsl(25, 90%, 55%)',
  'NFLX': 'hsl(0, 85%, 45%)',
  'PLTR': 'hsl(240, 60%, 50%)',
  'MARA': 'hsl(45, 80%, 45%)',
  'COIN': 'hsl(220, 70%, 50%)',
  'MU': 'hsl(180, 70%, 40%)',
  'SMCI': 'hsl(280, 60%, 50%)',
  'MSTR': 'hsl(35, 80%, 50%)',
  'ARM': 'hsl(200, 60%, 45%)',
};

export function getStockColor(symbol: string): string {
  return STOCK_COLORS[symbol] || `hsl(${Math.abs(hashCode(symbol)) % 360}, 70%, 50%)`;
}

function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash;
}

// 股票中文名稱映射
const STOCK_NAMES: Record<string, string> = {
  'TSM': '台積電',
  'NVDA': '輝達',
  'GOOGL': 'Google',
  'GOOG': 'Google',
  'AAPL': 'Apple',
  'MSFT': '微軟',
  'AMZN': '亞馬遜',
  'INTC': 'Intel',
  'AMD': 'AMD',
  'META': 'Meta',
  'TSLA': '特斯拉',
  'BABA': '阿里巴巴',
  'NFLX': 'Netflix',
  'PLTR': 'Palantir',
  'MARA': 'Marathon',
  'COIN': 'Coinbase',
  'MU': '美光',
  'SMCI': 'Super Micro',
  'MSTR': 'MicroStrategy',
  'ARM': 'ARM',
};

export function getStockName(symbol: string): string {
  return STOCK_NAMES[symbol] || symbol;
}

// API 調用函數
export async function fetchAvailableStocks(): Promise<Stock[]> {
  const response = await fetch('/api/stocks/available');
  if (!response.ok) {
    throw new Error('無法取得股票清單');
  }
  const data = await response.json();
  return data.map((s: any) => ({
    code: s.code,
    name: getStockName(s.code),
    price: s.price,
    vol90d: s.vol90d,
    iv: s.iv,
    color: getStockColor(s.code),
  }));
}

export async function generateBatchQuotes(params: AIFCNParams): Promise<BatchQuoteResponse> {
  // 前端驗證
  if (params.selectedStocks.length === 0) {
    throw new Error('請至少選擇一檔股票');
  }
  if (params.basketSizes.length === 0) {
    throw new Error('請至少選擇一種組合大小');
  }

  const response = await fetch('/api/fcn/batch-calculate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      stockPool: params.selectedStocks,
      basketSizes: params.basketSizes,
      period: params.tenor,
      strikePrice: params.strikePrice,
      knockOutPrice: params.knockOut,
      knockInPrice: params.knockIn,
      kiType: params.kiType,
      customFeeRate: params.cost,
      nonCallPeriods: params.nonCallPeriods,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    // 處理 Pydantic 驗證錯誤 (陣列格式)
    if (Array.isArray(error.detail)) {
      const messages = error.detail.map((e: any) => e.msg).join(', ');
      throw new Error(messages || '參數驗證失敗');
    }
    throw new Error(error.detail || '批次報價計算失敗');
  }

  return response.json();
}
