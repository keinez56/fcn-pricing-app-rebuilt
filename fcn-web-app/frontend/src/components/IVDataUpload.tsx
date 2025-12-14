import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileSpreadsheet, Trash2, Calendar, Check, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from '@/hooks/use-toast';

interface UploadResult {
  message: string;
  filename: string;
  date: string;
  stock_count: number;
  available_dates: string[];
}

export function IVDataUpload() {
  const [isOpen, setIsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 獲取可用日期列表
  const fetchDates = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/dates/available');
      if (response.ok) {
        const dates = await response.json();
        setAvailableDates(dates);
      }
    } catch (error) {
      console.error('Failed to fetch dates:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDates();
    }
  }, [isOpen]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 驗證檔案類型
    if (!file.name.endsWith('.xlsx')) {
      toast({
        title: '檔案格式錯誤',
        description: '只接受 .xlsx 格式的檔案',
        variant: 'destructive',
      });
      return;
    }

    // 驗證檔案名稱格式
    const filenameWithoutExt = file.name.replace('.xlsx', '');
    if (!/^\d{8}$/.test(filenameWithoutExt)) {
      toast({
        title: '檔案名稱格式錯誤',
        description: '檔案名稱必須是日期格式 (YYYYMMDD.xlsx)，例如 20251212.xlsx',
        variant: 'destructive',
      });
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/iv-data/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result: UploadResult = await response.json();
        setAvailableDates(result.available_dates);
        toast({
          title: '上傳成功',
          description: `已上傳 ${result.filename}，包含 ${result.stock_count} 檔股票資料`,
        });
      } else {
        const error = await response.json();
        toast({
          title: '上傳失敗',
          description: error.detail || '未知錯誤',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: '上傳失敗',
        description: '網路錯誤，請稍後再試',
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
      // 清除 input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (date: string) => {
    if (!confirm(`確定要刪除 ${date} 的資料嗎？`)) {
      return;
    }

    try {
      const response = await fetch(`/api/iv-data/${date}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const result = await response.json();
        setAvailableDates(result.available_dates);
        toast({
          title: '刪除成功',
          description: `已刪除 ${date} 的資料`,
        });
      } else {
        const error = await response.json();
        toast({
          title: '刪除失敗',
          description: error.detail || '未知錯誤',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: '刪除失敗',
        description: '網路錯誤，請稍後再試',
        variant: 'destructive',
      });
    }
  };

  const formatDate = (dateStr: string) => {
    // 將 YYYYMMDD 格式轉換為 YYYY/MM/DD
    return `${dateStr.slice(0, 4)}/${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}`;
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Upload className="h-4 w-4" />
          <span className="hidden sm:inline">上傳 IV 資料</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-primary" />
            IV 資料管理
          </DialogTitle>
          <DialogDescription>
            上傳 Bloomberg IV 資料檔案 (.xlsx)，檔案名稱必須是日期格式 (例如: 20251212.xlsx)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 上傳區域 */}
          <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              onChange={handleFileSelect}
              className="hidden"
              id="iv-file-input"
            />
            <label
              htmlFor="iv-file-input"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-8 w-8 text-primary animate-spin" />
                  <span className="text-sm text-muted-foreground">上傳中...</span>
                </>
              ) : (
                <>
                  <Upload className="h-8 w-8 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    點擊選擇檔案或拖曳檔案至此處
                  </span>
                  <span className="text-xs text-muted-foreground/70">
                    支援格式: .xlsx (例如: 20251212.xlsx)
                  </span>
                </>
              )}
            </label>
          </div>

          {/* 已上傳資料列表 */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              已上傳資料 ({availableDates.length} 筆)
            </h4>

            {loading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : availableDates.length > 0 ? (
              <div className="max-h-[200px] overflow-y-auto space-y-1">
                {availableDates.map((date, index) => (
                  <div
                    key={date}
                    className={`flex items-center justify-between px-3 py-2 rounded-md ${
                      index === 0 ? 'bg-primary/10 border border-primary/20' : 'bg-muted/30'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{formatDate(date)}</span>
                      {index === 0 && (
                        <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                          最新
                        </span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDelete(date)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-sm text-muted-foreground">
                尚無資料
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
