// 外部供应链风险数据获取 Hooks
import { useState, useEffect, useCallback, useRef } from "react";
import { alertDashboardApi } from "../lib/data";

// 活跃风险列表
export function useActiveRisks() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getActiveRisks();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching active risks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 风险统计数据
export function useRiskStatistics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getRiskStatistics();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching risk statistics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 风险趋势
export function useRiskTrend(days = 30) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getRiskTrend(days);
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching risk trend:', err);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 受影响供应商TOP5
export function useTopAffectedSuppliers() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getTopAffectedSuppliers();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching top affected suppliers:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 活跃风险数量
export function useActiveRiskCount() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getActiveRiskCount();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching active risk count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 高风险供应商数量
export function useHighRiskSupplierCount() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getHighRiskSupplierCount();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching high risk supplier count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}
