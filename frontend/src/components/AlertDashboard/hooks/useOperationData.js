// 供应链运营数据获取 Hooks
import { useState, useEffect, useCallback, useRef } from "react";
import { alertDashboardApi } from "../lib/data";

// 采购订单执行率
export function usePOExecutionRate() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getPOExecutionRate();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching PO execution rate:', err);
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

// 库存健康度
export function useInventoryHealthRate() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getInventoryHealthRate();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching inventory health rate:', err);
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

// 工单准时交付率
export function useWOOnTimeDeliveryRate() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getWOOnTimeDeliveryRate();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching WO on-time delivery rate:', err);
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

// 本月客户订单金额
export function useMonthlyCustomerOrderAmount() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getMonthlyCustomerOrderAmount();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching monthly customer order amount:', err);
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

// 延迟采购订单
export function useDelayedPurchaseOrders() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getDelayedPurchaseOrders();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching delayed purchase orders:', err);
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

// 供应商交付表现
export function useSupplierPerformance() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getSupplierPerformance();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching supplier performance:', err);
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

// 低库存预警
export function useLowInventoryAlerts() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getLowInventoryAlerts();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching low inventory alerts:', err);
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

// 延期工单
export function useDelayedWorkOrders() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getDelayedWorkOrders();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching delayed work orders:', err);
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

// 即将到期客户订单
export function useUpcomingCustomerOrders() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getUpcomingCustomerOrders();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching upcoming customer orders:', err);
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

// 客户订单交付趋势
export function useCustomerOrderTrend() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const hasLoaded = useRef(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getCustomerOrderTrend();
      setData(response.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching customer order trend:', err);
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
