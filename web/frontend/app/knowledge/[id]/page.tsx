'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  ArrowLeft,
  Calendar,
  FileText,
  Tag,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { knowledgeApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface KnowledgeDetail {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  content: string;
  updated_at: string;
  source?: string;
  file_path: string;
}

export default function KnowledgeDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [detail, setDetail] = useState<KnowledgeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDetail = async () => {
      try {
        setIsLoading(true);
        const response = await knowledgeApi.get(id);
        if (response) {
          setDetail(response);
        } else {
          setError('知识条目不存在');
        }
      } catch (error) {
        console.error('加载详情失败:', error);
        setError('加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      loadDetail();
    }
  }, [id]);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <span className="ml-2 text-primary-muted">加载中...</span>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="text-error mb-4">{error || '未找到'}</div>
        <Link href="/knowledge">
          <Button variant="secondary">
            <ArrowLeft className="w-4 h-4" />
            返回知识库
          </Button>
        </Link>
      </div>
    );
  }

  return (
      <div className="max-w-4xl mx-auto">
        {/* Back Button */}
        <Link href="/knowledge">
          <Button variant="ghost" size="sm" className="mb-6">
            <ArrowLeft className="w-4 h-4" />
            返回知识库
          </Button>
        </Link>

        {/* Header */}
        <div className="card mb-6">
          <h1 className="text-2xl font-bold text-primary mb-4">
            {detail.title}
          </h1>

          {/* Meta */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-primary-muted mb-4">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              更新于 {formatDate(detail.updated_at)}
            </span>
            {detail.source && (
              <span className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                来源: {detail.source.split('/').pop()}
              </span>
            )}
          </div>

          {/* Tags */}
          {detail.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <span className="flex items-center gap-1 text-sm text-primary-muted">
                <Tag className="w-4 h-4" />
                标签:
              </span>
              {detail.tags.map((tag) => (
                <Badge key={tag} variant="accent">
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {/* Summary */}
          {detail.summary && (
            <div className="mt-4 p-4 bg-surface-subtle rounded-lg">
              <p className="text-primary-muted text-sm">{detail.summary}</p>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-primary">文档内容</h2>
            <a
              href={`/api/files/${detail.file_path}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost btn-sm"
            >
              <ExternalLink className="w-4 h-4" />
              查看原始文件
            </a>
          </div>

          {/* Markdown Content */}
          <div className="prose prose-slate max-w-none">
            <pre className="whitespace-pre-wrap font-mono text-sm text-primary-muted bg-surface-subtle p-4 rounded-lg overflow-auto max-h-[600px]">
              {detail.content}
            </pre>
          </div>
        </div>
      </div>
  );
}
