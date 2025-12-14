import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export function LoadingOverlay() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm"
    >
      <div className="flex flex-col items-center gap-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="relative"
        >
          <div className="h-16 w-16 rounded-full border-4 border-blue-200" />
          <div className="absolute inset-0 h-16 w-16 rounded-full border-4 border-transparent border-t-blue-600 animate-spin" />
          <Sparkles className="absolute inset-0 m-auto h-6 w-6 text-blue-600" />
        </motion.div>
        <div className="text-center">
          <p className="text-lg font-medium text-gray-700">AI 智慧分析中...</p>
          <p className="text-sm text-gray-500">正在計算最佳組合</p>
        </div>
      </div>
    </motion.div>
  );
}
