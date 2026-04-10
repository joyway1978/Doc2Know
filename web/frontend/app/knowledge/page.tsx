'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Search,
  RefreshCw,
  FileText,
  Calendar,
  Tag,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { knowledgeApi } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface KnowledgeItem {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  file_path: string;
  updated_at: string;
  source?: string;
}

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<KnowledgeItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [total, setTotal] = useState(0);

  // 加载知识库数据
  const loadKnowledge = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: any = { page_size: 100 };
      if (searchQuery) params.search = searchQuery;
      if (selectedTag) params.tag = selectedTag;

      const response = await knowledgeApi.list(params);
      if (response?.items) {
        setItems(response.items);
        setFilteredItems(response.items);
        setTotal(response.total);
      }
    } catch (error) {
      console.error('加载知识库失败:', error);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedTag]);

  // 加载标签列表
  const loadTags = useCallback(async () => {
    try {
      const response = await knowledgeApi.getTags();
      if (response?.tags) {
        setTags(response.tags);
      }
    } catch (error) {
      console.error('加载标签失败:', error);
    }
  }, []);

  useEffect(() => {
    loadKnowledge();
  }, [loadKnowledge]);

  useEffect(() => {
    loadTags();
  }, [loadTags]);

  // 重建索引
  const handleRebuildIndex = async () => {
    if (!confirm('确定要重建知识库索引吗？')) return;

    try {
      setIsLoading(true);
      await knowledgeApi.rebuildIndex();
      loadKnowledge();
      alert('索引重建完成');
    } catch (error) {
      console.error('重建索引失败:', error);
      alert('重建索引失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 搜索处理
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadKnowledge();
  };

  // 标签筛选
  const handleTagClick = (tag: string) => {
    if (selectedTag === tag) {
      setSelectedTag(null);
    } else {
      setSelectedTag(tag);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-primary">知识库</h1>
          <p className="text-primary-muted mt-1">
            共 {total} 篇文档
            {selectedTag && ` · 标签: ${selectedTag}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={loadKnowledge}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRebuildIndex}
            disabled={isLoading}
          >
            <BookOpen className="w-4 h-4" />
            重建索引
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card mb-8">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary-muted" />
            <input
              type="text"
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
            />
          </div>
          <Button type="submit" variant="primary" size="md">
            搜索
          </Button>
        </form>

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex items-start gap-2 flex-wrap">
            <span className="text-sm text-primary-muted flex items-center gap-1 pt-1">
              <Tag className="w-4 h-4" />
              标签:
            </span>
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => handleTagClick(tag)}
                className={`text-sm px-2 py-1 rounded-full transition-colors ${
                  selectedTag === tag
                    ? 'bg-accent text-white'
                    : 'bg-surface-subtle text-primary-muted hover:bg-border'
                }`}
              >
                {tag}
              </button>
            ))}
            {selectedTag && (
              <button
                onClick={() => setSelectedTag(null)}
                className="text-sm text-accent hover:underline"
              >
                清除筛选
              </button>
            )}
          </div>
        )}
      </div>

      {/* Knowledge Grid */}
      {filteredItems.length === 0 ? (
        <div className="card text-center py-12">
          <BookOpen className="w-12 h-12 text-border mx-auto mb-4" />
          <p className="text-primary-muted">
            {searchQuery || selectedTag
              ? '没有找到匹配的知识条目'
              : '知识库为空，请先上传并处理文档'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredItems.map((item) => (
            <Link
              key={item.id}
              href={`/knowledge/${item.id}`}
              className="card hover:border-accent hover:shadow-md transition-all cursor-pointer group"
            >
              {/* Title */}
              <h3 className="font-semibold text-primary mb-2 group-hover:text-accent transition-colors">
                {item.title}
              </h3>

              {/* Summary */}
              <p className="text-sm text-primary-muted line-clamp-3 mb-4">
                {item.summary || '暂无摘要'}
              </p>

              {/* Tags */}
              {item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-4">
                  {item.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="default" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {item.tags.length > 3 && (
                    <Badge variant="default" className="text-xs">
                      +{item.tags.length - 3}
                    </Badge>
                  )}
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-between text-xs text-primary-muted pt-3 border-t border-border">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {formatDate(item.updated_at)}
                </span>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
