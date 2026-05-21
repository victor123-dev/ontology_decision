// 指标树数据 hook
// 从后端获取完整的指标树数据
import { useState, useEffect, useCallback } from 'react';
import { alertDashboardApi } from '../lib/data';

export function useMetricTree() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await alertDashboardApi.getMetricTree();
      setData(response.data);
    } catch (err) {
      console.error('获取指标树数据失败:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
