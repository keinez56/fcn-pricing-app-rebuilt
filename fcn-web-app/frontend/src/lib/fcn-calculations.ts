export interface FCNParameters {
  underlyingAssets: string[];
  strikePrice: number;
  knockOutBarrier: number;
  knockInBarrier: number;
  barrierType: 'EKI' | 'AKI';
  issuePrice: number;
  tenor: number;
  protectionPeriod: number;
}

export const defaultFCNParameters: FCNParameters = {
  underlyingAssets: ['TSLA', 'NVDA', 'AAPL'],
  strikePrice: 100,
  knockOutBarrier: 105,
  knockInBarrier: 70,
  barrierType: 'EKI',
  issuePrice: 100,
  tenor: 6,
  protectionPeriod: 1,
};

export interface QuoteResult {
  annualizedCoupon: number;
  riskLevel: 'Low' | 'Medium' | 'High';
  worstCaseReturn: number;
  bestCaseReturn: number;
}

// 本地計算函數 (用於即時預覽，實際報價會使用後端 API)
export function calculateQuote(params: FCNParameters): QuoteResult {
  // Base coupon starts at 8%
  let baseCoupon = 8;

  // Lower strike = Lower risk = Lower coupon
  const strikeAdjustment = (100 - params.strikePrice) * 0.15;

  // Lower KI = Lower risk = Lower coupon
  const kiAdjustment = (100 - params.knockInBarrier) * 0.12;

  // Higher KO = Higher probability of early termination = Lower coupon
  const koAdjustment = (params.knockOutBarrier - 100) * -0.1;

  // Longer tenor = Higher coupon
  const tenorAdjustment = (params.tenor - 6) * 0.3;

  // More underlying assets = More risk = Higher coupon
  const assetAdjustment = (params.underlyingAssets.length - 1) * 1.5;

  // AKI is riskier = Higher coupon
  const barrierTypeAdjustment = params.barrierType === 'AKI' ? 1.2 : 0;

  // Add some randomness for simulation feel
  const volatilityFactor = 0.95 + Math.random() * 0.1;

  const finalCoupon = (baseCoupon + strikeAdjustment + kiAdjustment + koAdjustment + tenorAdjustment + assetAdjustment + barrierTypeAdjustment) * volatilityFactor;

  // Determine risk level
  let riskLevel: 'Low' | 'Medium' | 'High' = 'Medium';
  if (params.strikePrice >= 90 && params.knockInBarrier >= 80) {
    riskLevel = 'Low';
  } else if (params.strikePrice <= 70 || params.knockInBarrier <= 60) {
    riskLevel = 'High';
  }

  // Calculate returns
  const bestCaseReturn = finalCoupon * (params.tenor / 12); // Full coupon payment
  const worstCaseReturn = -(100 - bestCaseReturn); // Stock goes to zero: lose 100% minus coupon earned

  return {
    annualizedCoupon: Math.max(4, Math.min(25, finalCoupon)),
    riskLevel,
    worstCaseReturn,
    bestCaseReturn,
  };
}

export interface PayoffDataPoint {
  stockPerformance: number;
  redemptionAmount: number;
}

export function generatePayoffData(params: FCNParameters, couponReturn: number = 0): PayoffDataPoint[] {
  const data: PayoffDataPoint[] = [];

  for (let perf = 0; perf <= 130; perf += 2) {
    let redemption: number;

    if (perf >= params.knockOutBarrier) {
      // KO triggered - early redemption at 100% + coupon
      redemption = 100 + couponReturn;
    } else if (perf >= params.strikePrice) {
      // Above strike, no KI - full redemption + coupon
      redemption = 100 + couponReturn;
    } else if (perf >= params.knockInBarrier) {
      // Between KI and Strike - partial loss + coupon
      redemption = 100 - (params.strikePrice - perf) * 0.5 + couponReturn;
    } else {
      // Below KI - physical delivery / loss + coupon
      redemption = (perf / params.strikePrice) * 100 + couponReturn;
    }

    data.push({
      stockPerformance: perf,
      redemptionAmount: Math.max(0, redemption),
    });
  }

  return data;
}
