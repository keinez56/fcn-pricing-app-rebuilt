interface BasketSizeSelectProps {
  selected: number[];
  onChange: (sizes: number[]) => void;
  maxSize: number;
}

export function BasketSizeSelect({ selected, onChange, maxSize }: BasketSizeSelectProps) {
  const sizes = [1, 2, 3, 4];

  const toggleSize = (size: number) => {
    if (selected.includes(size)) {
      onChange(selected.filter(s => s !== size));
    } else {
      onChange([...selected, size].sort((a, b) => a - b));
    }
  };

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium">連結標的數量</label>
      <p className="text-xs text-gray-500">選擇要產生的組合大小（可複選）</p>

      <div className="flex gap-2">
        {sizes.map((size) => {
          const isDisabled = size > maxSize;
          const isSelected = selected.includes(size);

          return (
            <button
              key={size}
              onClick={() => !isDisabled && toggleSize(size)}
              disabled={isDisabled}
              className={`
                flex-1 h-12 rounded-lg border-2 font-bold text-lg transition-all
                ${isDisabled && 'opacity-40 cursor-not-allowed'}
                ${isSelected
                  ? 'border-blue-500 bg-blue-500 text-white'
                  : 'border-gray-200 hover:border-blue-300'
                }
              `}
            >
              {size}
            </button>
          );
        })}
      </div>

      {maxSize < 4 && (
        <p className="text-xs text-amber-600">
          需選擇至少 {5 - maxSize} 檔以上股票才能解鎖更多選項
        </p>
      )}

      {selected.length > 0 && (
        <p className="text-xs text-gray-500">
          將產生：
          {selected.map((size, idx) => (
            <span key={size}>
              {idx > 0 && ' + '}
              <span className="font-medium">C({maxSize},{size})</span>
            </span>
          ))}
          種組合
        </p>
      )}
    </div>
  );
}
