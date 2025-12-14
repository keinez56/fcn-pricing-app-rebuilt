import { motion } from 'framer-motion';
import { Grid3X3 } from 'lucide-react';
import { type FCNQuote } from '@/lib/ai-fcn-utils';
import { QuoteCard } from './QuoteCard';

interface AllQuotesGridProps {
  quotes: FCNQuote[];
}

export function AllQuotesGrid({ quotes }: AllQuotesGridProps) {
  const remainingQuotes = quotes.slice(15);

  if (remainingQuotes.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <Grid3X3 className="h-5 w-5 text-gray-500" />
        <h2 className="text-lg font-semibold">其他組合</h2>
        <span className="text-sm text-gray-500">
          ({remainingQuotes.length} 個)
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {remainingQuotes.map((quote, index) => (
          <QuoteCard
            key={quote.id}
            quote={quote}
            index={index + 15}
          />
        ))}
      </div>
    </motion.div>
  );
}
