import { motion } from 'framer-motion';
import { Trophy, Sparkles } from 'lucide-react';
import { type FCNQuote } from '@/lib/ai-fcn-utils';
import { QuoteCard } from './QuoteCard';

interface TopPicksSectionProps {
  quotes: FCNQuote[];
}

export function TopPicksSection({ quotes }: TopPicksSectionProps) {
  const topPicks = quotes.slice(0, 15);

  if (topPicks.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <Trophy className="h-5 w-5 text-amber-500" />
        <h2 className="text-lg font-semibold">Top 15 推薦組合</h2>
        <Sparkles className="h-4 w-4 text-blue-500 animate-pulse" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {topPicks.map((quote, index) => (
          <QuoteCard
            key={quote.id}
            quote={quote}
            index={index}
            isTopPick={index < 3}
          />
        ))}
      </div>
    </motion.div>
  );
}
