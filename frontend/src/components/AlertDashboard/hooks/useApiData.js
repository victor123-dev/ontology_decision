// 供应链控制塔 - 数据获取 Hooks
import { useState, useEffect, useCallback, useRef } from "react";
import { alertDashboardApi } from "../lib/data";

// KPI 单个指标 hooks
export function usePurchaseOnTimeRate() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getPurchaseOnTimeRate();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching purchase on time rate:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// 合并的销售数据 Hook
export function useMonthlySales() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getMonthlySales();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching monthly sales:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useAlertCount() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getAlertCount();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching alert count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useAlertExecCount() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getAlertExecCount();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching alert exec count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

// KPI 数据 - 整体API（保留以兼容）
export function useKpiData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getKpiData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching KPI data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useChartData() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getChartData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching chart data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useLogisticsData() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getLogisticsData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching logistics data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useForecastData() {
  const [data, setData] = useState({ months: [], data: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getForecastData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching forecast data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useMapData() {
  const [data, setData] = useState({ nodes: [], routes: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getMapData();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching map data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useAlertMessages() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getAlertMessages();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching alert messages:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 避免在 React StrictMode 下重复请求
    if (!hasLoaded.current) {
      hasLoaded.current = true;
      loadData();
    }
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}
