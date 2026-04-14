// 供应链控制塔 - 数据获取 Hooks
import { useState, useEffect, useCallback } from "react";
import { alertDashboardApi } from "../lib/data";

export function useKpiData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useChartData() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useLogisticsData() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useForecastData() {
  const [data, setData] = useState({ months: [], data: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useMapData() {
  const [data, setData] = useState({ nodes: [], routes: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

export function useAlertMessages() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}
