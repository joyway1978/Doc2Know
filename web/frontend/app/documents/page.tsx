'use client';

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import {
  Upload,
  FileText,
  RefreshCw,
  Trash2,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { documentsApi } from '@/lib/api';
import {
  formatFileSize,
  formatRelativeTime,
  getStatusColor,
  getStatusText,
} from '@/lib/utils';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  file_type: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  error_message?: string;
  output_file?: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, number>>(new Map());

  // 加载文档列表
  const loadDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await documentsApi.list({ page_size: 50 });
      if (response?.items) {
        setDocuments(response.items);
      }
    } catch (error) {
      console.error('加载文档失败:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    // 定时刷新
    const interval = setInterval(loadDocuments, 3000);
    return () => clearInterval(interval);
  }, [loadDocuments]);

  // 处理文件上传
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    for (const file of Array.from(files)) {
      // 检查文件类型
      const allowedTypes = ['.docx', '.doc', '.pdf'];
      const fileExt = file.name.toLowerCase();
      if (!allowedTypes.some(ext => fileExt.endsWith(ext))) {
        alert(`不支持的文件类型: ${file.name}`);
        continue;
      }

      const uploadId = `${file.name}-${Date.now()}`;
      setUploadingFiles(prev => new Map(prev).set(uploadId, 0));

      try {
        const response = await documentsApi.upload(file);
        console.log('上传成功:', response);
      } catch (error) {
        console.error('上传失败:', error);
        alert(`上传失败: ${file.name}`);
      } finally {
        setUploadingFiles(prev => {
          const next = new Map(prev);
          next.delete(uploadId);
          return next;
        });
      }
    }

    // 刷新列表
    loadDocuments();
  };

  // 拖放处理
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e.dataTransfer.files);
  };

  // 删除文档
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个文档吗？')) return;

    try {
      await documentsApi.delete(id);
      loadDocuments();
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败');
    }
  };

  // 重试处理
  const handleRetry = async (id: string) => {
    try {
      await documentsApi.retry(id);
      loadDocuments();
    } catch (error) {
      console.error('重试失败:', error);
      alert('重试失败');
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-primary">文档管理</h1>
        <Button
          variant="secondary"
          size="sm"
          onClick={loadDocuments}
          disabled={isLoading}
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone mb-8 ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="text-4xl mb-4">📁</div>
        <p className="font-medium text-primary mb-2">拖放文件到此处上传</p>
        <p className="text-sm text-primary-muted mb-4">
          支持 .docx, .doc, .pdf 格式
        </p>
        <label className="cursor-pointer inline-flex">
          <input
            id="file-upload"
            type="file"
            accept=".docx,.doc,.pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          <span className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md bg-accent text-white hover:bg-accent-hover transition-colors">
            <Upload className="w-4 h-4" />
            选择文件
          </span>
        </label>
      </div>

      {/* Uploading Files */}
      {uploadingFiles.size > 0 && (
        <div className="card mb-8">
          <h3 className="font-medium text-primary mb-4">上传中</h3>
          <div className="space-y-4">
            {Array.from(uploadingFiles.entries()).map(([id, progress]) => (
              <div key={id} className="flex items-center gap-4">
                <Loader2 className="w-5 h-5 text-accent animate-spin" />
                <div className="flex-1">
                  <div className="text-sm font-medium">{id.split('-')[0]}</div>
                  <Progress value={progress} showLabel className="mt-2" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Document List */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-primary">
          文档列表 ({documents.length})
        </h2>

        {documents.length === 0 ? (
          <div className="card text-center py-12">
            <FileText className="w-12 h-12 text-border mx-auto mb-4" />
            <p className="text-primary-muted">暂无文档，请上传文件</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="card flex items-center gap-4 hover:border-accent transition-colors"
              >
                {/* File Icon */}
                <div className="w-10 h-10 rounded-lg bg-surface-subtle flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-primary-muted" />
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-primary truncate">
                      {doc.filename}
                    </h3>
                    <Badge
                      variant={
                        doc.status === 'completed'
                          ? 'success'
                          : doc.status === 'failed'
                          ? 'error'
                          : doc.status === 'processing'
                          ? 'accent'
                          : 'default'
                      }
                      className="flex-shrink-0"
                    >
                      {getStatusText(doc.status)}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-primary-muted mt-1">
                    <span>{formatFileSize(doc.file_size)}</span>
                    <span>{formatRelativeTime(doc.created_at)}</span>
                    {doc.error_message && (
                      <span className="text-error">{doc.error_message}</span>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {doc.status === 'processing' && (
                    <div className="mt-3">
                      <Progress value={doc.progress} showLabel />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {doc.status === 'failed' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRetry(doc.id)}
                      title="重试"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                  )}
                  {doc.status === 'completed' && doc.output_file && (
                    <a
                      href={`/files/${doc.output_file.replace(/^.*[\\/]/, '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-ghost btn-sm"
                    >
                      <CheckCircle className="w-4 h-4 text-success" />
                      查看
                    </a>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(doc.id)}
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4 text-error" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
