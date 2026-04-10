'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  FileText,
  BookOpen,
  CheckCircle,
  AlertCircle,
  Loader2,
  Upload,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { configApi, documentsApi, knowledgeApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface Stats {
  total_documents: number;
  completed: number;
  processing: number;
  failed: number;
  total_knowledge_items: number;
  last_updated?: string;
}

interface RecentDocument {
  id: string;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
}

export default function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentDocs, setRecentDocs] = useState<RecentDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);

      // 加载统计信息
      const statsRes = await configApi.getStats();
      if (statsRes) {
        setStats(statsRes);
      }

      // 加载健康状态
      const healthRes = await configApi.health();
      setHealth(healthRes);

      // 加载最近文档
      const docsRes = await documentsApi.list({ page_size: 5 });
      if (docsRes?.items) {
        setRecentDocs(docsRes.items);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 定时刷新
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading && !stats) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <span className="ml-2 text-primary-muted">加载中...</span>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary mb-2">
          欢迎使用 Doc2Know
        </h1>
        <p className="text-primary-muted">
          AI 驱动的文档转换工具，将 Word 文档转换为结构化知识库
        </p>
      </div>

      {/* Status Banner */}
      {health && health.status === 'degraded' && (
        <div className="card mb-8 border-warning bg-yellow-50">
          <div className="flex items-center gap-2 text-warning">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">系统状态异常</span>
          </div>
          {health.issues && (
            <ul className="mt-2 text-sm text-primary-muted">
              {health.issues.map((issue: string, idx: number) => (
                <li key={idx}>• {issue}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <FileText className="w-5 h-5 text-accent" />
            </div>
            <span className="text-primary-muted text-sm">总文档数</span>
          </div>
          <p className="text-2xl font-bold text-primary">
            {stats?.total_documents || 0}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-success" />
            </div>
            <span className="text-primary-muted text-sm">已完成</span>
          </div>
          <p className="text-2xl font-bold text-primary">
            {stats?.completed || 0}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-purple-600" />
            </div>
            <span className="text-primary-muted text-sm">知识条目</span>
          </div>
          <p className="text-2xl font-bold text-primary">
            {stats?.total_knowledge_items || 0}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-error" />
            </div>
            <span className="text-primary-muted text-sm">失败</span>
          </div>
          <p className="text-2xl font-bold text-primary">
            {stats?.failed || 0}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-primary mb-4">快速操作</h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/documents">
            <Button variant="primary">
              <Upload className="w-4 h-4" />
              上传文档
            </Button>
          </Link>
          <Link href="/knowledge">
            <Button variant="secondary">
              <BookOpen className="w-4 h-4" />
              浏览知识库
            </Button>
          </Link>
          <Button
            variant="ghost"
            onClick={loadData}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新数据
          </Button>
        </div>
      </div>

      {/* Recent Documents */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary">最近文档</h2>
          <Link href="/documents">
            <Button variant="ghost" size="sm">
              查看全部
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>

        {recentDocs.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-10 h-10 text-border mx-auto mb-3" />
            <p className="text-primary-muted text-sm">暂无文档</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentDocs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-4 p-3 bg-surface-subtle rounded-lg"
              >
                <FileText className="w-5 h-5 text-primary-muted" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-primary truncate">
                    {doc.filename}
                  </p>
                  <p className="text-xs text-primary-muted">
                    {formatDate(doc.created_at)}
                  </p>
                </div>
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
                >
                  {doc.status === 'completed' && '已完成'}
                  {doc.status === 'failed' && '失败'}
                  {doc.status === 'processing' && `处理中 ${doc.progress}%`}
                  {doc.status === 'pending' && '等待中'}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
