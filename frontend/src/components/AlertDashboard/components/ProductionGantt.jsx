import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, ZoomIn, ZoomOut, RefreshCw, AlertCircle, MoveHorizontal } from 'lucide-react';
import { alertDashboardApi } from '../lib/data';

const DEFAULT_BASE_DATE = '2026-04-25';
const DEFAULT_DAYS = 7;
const ROW_HEIGHT = 58;
const HEADER_HEIGHT = 54;
const RESOURCE_WIDTH = 220;
const OVERSCAN = 8;
const MIN_TASK_WIDTH = 6;
const MIN_TASK_DURATION_MS = 5 * 60 * 1000;
const ZOOM_LEVELS = [24, 36, 54, 72, 96, 128];
const cache = new Map();

const statusColors = {
  已排程: { background: '#2563eb', border: '#60a5fa' },
  生产中: { background: '#f59e0b', border: '#fbbf24' },
  已完成: { background: '#10b981', border: '#34d399' },
  已延迟: { background: '#ef4444', border: '#f87171' },
  暂停: { background: '#8b5cf6', border: '#a78bfa' },
  未开始: { background: '#64748b', border: '#94a3b8' },
};

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function formatDateOnly(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatDateLabel(date) {
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', weekday: 'short' });
}

function formatTimeLabel(date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr;
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function normalizeDate(value, fallback) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return date;
}

function snapDate(date) {
  const step = 15 * 60 * 1000;
  return new Date(Math.round(date.getTime() / step) * step);
}

function validatePayload(payload) {
  if (!payload || typeof payload !== 'object') throw new Error('接口返回数据为空或格式错误');
  if (!payload.time_range || !payload.time_range.start || !payload.time_range.end) throw new Error('缺少 time_range.start 或 time_range.end');
  if (!Array.isArray(payload.resources)) throw new Error('resources 必须是数组');
  if (!Array.isArray(payload.tasks)) throw new Error('tasks 必须是数组');
  return payload;
}

function getStatusColor(status) {
  return statusColors[status] || { background: '#3b82f6', border: '#93c5fd' };
}

function getProgressValue(progress) {
  const value = Number(progress);
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function getTaskTime(task) {
  const start = new Date(task.start);
  const end = new Date(task.end);
  return {
    start: Number.isNaN(start.getTime()) ? null : start,
    end: Number.isNaN(end.getTime()) ? null : end,
  };
}

function buildTimelineTicks(start, end, pxPerHour) {
  const totalHours = Math.ceil((end - start) / 3600000);
  const hourStep = pxPerHour >= 96 ? 1 : pxPerHour >= 54 ? 2 : pxPerHour >= 36 ? 4 : 6;
  const ticks = [];
  const first = new Date(start);
  first.setMinutes(0, 0, 0);
  if (first < start) first.setHours(first.getHours() + 1);
  for (let cursor = first; cursor <= end; cursor = new Date(cursor.getTime() + hourStep * 3600000)) {
    ticks.push(new Date(cursor));
  }
  return { ticks, totalHours, hourStep };
}

export default function ProductionGantt({ refreshTrigger }) {
  const [viewType, setViewType] = useState('work_order');
  const [baseDate, setBaseDate] = useState(DEFAULT_BASE_DATE);
  const [days] = useState(DEFAULT_DAYS);
  const [zoomIndex, setZoomIndex] = useState(2);
  const [data, setData] = useState(null);
  const [localTasks, setLocalTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(320);
  const [tooltip, setTooltip] = useState(null);
  const [dragState, setDragState] = useState(null);
  const bodyRef = useRef(null);
  const abortRef = useRef(null);

  const pxPerHour = ZOOM_LEVELS[zoomIndex];

  const loadData = useCallback(async (force = false) => {
    const key = `${viewType}|${baseDate}|${days}`;
    if (!force && cache.has(key)) {
      const cached = cache.get(key);
      setData(cached);
      setLocalTasks(cached.tasks);
      setLoading(false);
      setError(null);
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setLoading(true);
      setError(null);
      const response = await alertDashboardApi.getProductionGantt(viewType, baseDate, days, controller.signal);
      const payload = validatePayload(response.data);
      const normalized = {
        ...payload,
        resources: payload.resources.map(resource => ({
          id: String(resource.id ?? ''),
          name: String(resource.name ?? resource.id ?? ''),
          type: resource.type ?? viewType,
        })),
        tasks: payload.tasks.map(task => ({
          ...task,
          id: String(task.id ?? `${task.resource_id}-${task.start}-${task.end}`),
          resource_id: String(task.resource_id ?? ''),
        })),
      };
      cache.set(key, normalized);
      setData(normalized);
      setLocalTasks(normalized.tasks);
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') return;
      setError(err.response?.data?.detail || err.message || '甘特图数据加载失败');
      setData(null);
      setLocalTasks([]);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [baseDate, days, viewType]);

  useEffect(() => {
    loadData(false);
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [loadData]);

  useEffect(() => {
    if (refreshTrigger > 0) loadData(true);
  }, [refreshTrigger, loadData]);

  useEffect(() => {
    const node = bodyRef.current;
    if (!node) return undefined;
    const update = () => setViewportHeight(node.clientHeight || 320);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!dragState) return undefined;

    const handleMouseMove = event => {
      const deltaPx = event.clientX - dragState.startX;
      const deltaMs = (deltaPx / pxPerHour) * 3600000;
      setLocalTasks(tasks => tasks.map(task => {
        if (task.id !== dragState.task.id) return task;
        const originalStart = new Date(dragState.task.start);
        const originalEnd = new Date(dragState.task.end);
        let nextStart = originalStart;
        let nextEnd = originalEnd;
        if (dragState.mode === 'move') {
          nextStart = snapDate(new Date(originalStart.getTime() + deltaMs));
          nextEnd = snapDate(new Date(originalEnd.getTime() + deltaMs));
        }
        if (dragState.mode === 'start') {
          nextStart = snapDate(new Date(originalStart.getTime() + deltaMs));
          if (nextEnd.getTime() - nextStart.getTime() < MIN_TASK_DURATION_MS) {
            nextStart = new Date(nextEnd.getTime() - MIN_TASK_DURATION_MS);
          }
        }
        if (dragState.mode === 'end') {
          nextEnd = snapDate(new Date(originalEnd.getTime() + deltaMs));
          if (nextEnd.getTime() - nextStart.getTime() < MIN_TASK_DURATION_MS) {
            nextEnd = new Date(nextStart.getTime() + MIN_TASK_DURATION_MS);
          }
        }
        return { ...task, start: nextStart.toISOString(), end: nextEnd.toISOString() };
      }));
    };

    const handleMouseUp = () => setDragState(null);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragState, pxPerHour]);

  const timeRange = useMemo(() => {
    const baseStart = new Date(`${baseDate}T00:00:00`);
    const fallbackStart = Number.isNaN(baseStart.getTime()) ? new Date(`${DEFAULT_BASE_DATE}T00:00:00`) : baseStart;
    const fallbackEnd = addDays(fallbackStart, days);
    return {
      start: normalizeDate(data?.time_range?.start, fallbackStart),
      end: normalizeDate(data?.time_range?.end, fallbackEnd),
    };
  }, [baseDate, data, days]);

  const timeline = useMemo(() => buildTimelineTicks(timeRange.start, timeRange.end, pxPerHour), [timeRange.start, timeRange.end, pxPerHour]);
  const timelineWidth = Math.max((timeRange.end - timeRange.start) / 3600000 * pxPerHour, 680);

  const resourcesWithTasks = useMemo(() => {
    const taskMap = new Map();
    for (const task of localTasks) {
      if (!taskMap.has(task.resource_id)) taskMap.set(task.resource_id, []);
      taskMap.get(task.resource_id).push(task);
    }
    return (data?.resources || []).map(resource => ({
      ...resource,
      tasks: (taskMap.get(resource.id) || []).slice().sort((a, b) => new Date(a.start) - new Date(b.start)),
    }));
  }, [data, localTasks]);

  const visibleRange = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const count = Math.ceil(viewportHeight / ROW_HEIGHT) + OVERSCAN * 2;
    const end = Math.min(resourcesWithTasks.length, start + count);
    return { start, end };
  }, [resourcesWithTasks.length, scrollTop, viewportHeight]);

  const visibleResources = resourcesWithTasks.slice(visibleRange.start, visibleRange.end);

  const handleScroll = event => {
    setScrollTop(event.currentTarget.scrollTop);
    setScrollLeft(event.currentTarget.scrollLeft);
    setTooltip(null);
  };

  const handleMouseDown = (event, task, mode) => {
    event.preventDefault();
    event.stopPropagation();
    setTooltip(null);
    setDragState({ startX: event.clientX, task, mode });
  };

  const showTooltip = (event, task) => {
    setTooltip({ task, x: event.clientX + 14, y: event.clientY + 14 });
  };

  const moveTooltip = event => {
    setTooltip(current => current ? { ...current, x: event.clientX + 14, y: event.clientY + 14 } : current);
  };

  const empty = !loading && !error && resourcesWithTasks.length === 0;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', color: '#cbd5e1', fontSize: 11, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '8px 10px', borderBottom: '1px solid rgba(59,130,246,0.16)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <button onMouseDown={e => e.stopPropagation()} onClick={() => setViewType('machine')} style={viewType === 'machine' ? styles.activeButton : styles.button}>机台视图</button>
          <button onMouseDown={e => e.stopPropagation()} onClick={() => setViewType('work_order')} style={viewType === 'work_order' ? styles.activeButton : styles.button}>工单视图</button>
          <span style={{ color: '#64748b', padding: '0 4px' }}>|</span>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#94a3b8' }}>
            基准日期
            <input
              type="date"
              value={baseDate}
              onMouseDown={e => e.stopPropagation()}
              onChange={e => setBaseDate(e.target.value || DEFAULT_BASE_DATE)}
              style={styles.dateInput}
            />
          </label>
          <span style={{ color: '#64748b' }}>起 {days} 天</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button onMouseDown={e => e.stopPropagation()} onClick={() => setZoomIndex(value => Math.max(0, value - 1))} style={styles.iconButton} title="缩小"><ZoomOut size={13} /></button>
          <span style={{ color: '#64748b', minWidth: 52, textAlign: 'center' }}>{pxPerHour}px/h</span>
          <button onMouseDown={e => e.stopPropagation()} onClick={() => setZoomIndex(value => Math.min(ZOOM_LEVELS.length - 1, value + 1))} style={styles.iconButton} title="放大"><ZoomIn size={13} /></button>
          <button onMouseDown={e => e.stopPropagation()} onClick={() => loadData(true)} style={styles.button}><RefreshCw size={12} />刷新</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: `${RESOURCE_WIDTH}px minmax(0, 1fr)`, height: HEADER_HEIGHT, borderBottom: '1px solid rgba(59,130,246,0.18)', flexShrink: 0, background: 'rgba(15,23,42,0.86)' }}>
        <div style={{ padding: '8px 10px', borderRight: '1px solid rgba(59,130,246,0.18)', color: '#93c5fd', fontWeight: 600 }}>
          资源（{viewType === 'machine' ? '机台' : '工单'}）
          <div style={{ color: '#64748b', fontWeight: 400, marginTop: 4 }}>共 {resourcesWithTasks.length} 行 / {localTasks.length} 个任务</div>
        </div>
        <div style={{ overflow: 'hidden' }}>
          <div style={{ position: 'relative', width: timelineWidth, height: '100%', transform: `translateX(${-scrollLeft}px)` }}>
            {Array.from({ length: days }).map((_, index) => {
              const day = addDays(timeRange.start, index);
              return (
                <div key={formatDateOnly(day)} style={{ position: 'absolute', left: index * 24 * pxPerHour, top: 0, width: 24 * pxPerHour, height: 24, borderRight: '1px solid rgba(59,130,246,0.18)', paddingLeft: 6, color: '#bfdbfe', fontWeight: 600 }}>
                  {formatDateLabel(day)}
                </div>
              );
            })}
            {timeline.ticks.map(tick => {
              const left = (tick - timeRange.start) / 3600000 * pxPerHour;
              return (
                <div key={tick.toISOString()} style={{ position: 'absolute', left, top: 26, width: Math.max(timeline.hourStep * pxPerHour, 1), height: 26, borderLeft: '1px solid rgba(148,163,184,0.15)', paddingLeft: 4, color: '#64748b' }}>
                  {formatTimeLabel(tick)}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div ref={bodyRef} onScroll={handleScroll} style={{ flex: 1, minHeight: 0, overflow: 'auto', position: 'relative' }}>
        {loading && <StateMessage icon={<RefreshCw size={18} style={{ animation: 'spin 1s linear infinite' }} />} title="正在加载生产排程" text="正在获取资源与任务数据" />}
        {error && <StateMessage icon={<AlertCircle size={18} />} title="甘特图加载失败" text={error} danger />}
        {empty && <StateMessage icon={<CalendarDays size={18} />} title="暂无排程数据" text="当前视图与时间范围内没有可展示的资源或任务" />}

        {!loading && !error && !empty && (
          <div style={{ width: RESOURCE_WIDTH + timelineWidth, height: resourcesWithTasks.length * ROW_HEIGHT, position: 'relative' }}>
            <div style={{ transform: `translateY(${visibleRange.start * ROW_HEIGHT}px)` }}>
              {visibleResources.map((resource, offset) => {
                const rowIndex = visibleRange.start + offset;
                return (
                  <div key={resource.id} style={{ display: 'grid', gridTemplateColumns: `${RESOURCE_WIDTH}px ${timelineWidth}px`, height: ROW_HEIGHT, background: rowIndex % 2 === 0 ? 'rgba(15,23,42,0.42)' : 'rgba(30,41,59,0.34)', borderBottom: '1px solid rgba(59,130,246,0.08)' }}>
                    <div style={{ position: 'sticky', left: 0, zIndex: 3, padding: '8px 10px', borderRight: '1px solid rgba(59,130,246,0.16)', background: rowIndex % 2 === 0 ? '#101b31' : '#132038', overflow: 'hidden' }}>
                      <div style={{ color: '#e2e8f0', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{resource.id}</div>
                      <div style={{ color: '#94a3b8', marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{resource.name}</div>
                    </div>
                    <div style={{ position: 'relative', overflow: 'hidden' }}>
                      {timeline.ticks.map(tick => {
                        const left = (tick - timeRange.start) / 3600000 * pxPerHour;
                        return <div key={tick.toISOString()} style={{ position: 'absolute', left, top: 0, bottom: 0, borderLeft: '1px solid rgba(148,163,184,0.06)' }} />;
                      })}
                      {resource.tasks.map(task => {
                        const taskTime = getTaskTime(task);
                        if (!taskTime.start || !taskTime.end) return null;
                        const left = (taskTime.start - timeRange.start) / 3600000 * pxPerHour;
                        const width = Math.max((taskTime.end - taskTime.start) / 3600000 * pxPerHour, MIN_TASK_WIDTH);
                        if (left + width < 0 || left > timelineWidth) return null;
                        const color = getStatusColor(task.status);
                        const progress = getProgressValue(task.progress);
                        return (
                          <div key={task.id} onMouseEnter={event => showTooltip(event, task)} onMouseMove={moveTooltip} onMouseLeave={() => setTooltip(null)} onMouseDown={event => handleMouseDown(event, task, 'move')} style={{ position: 'absolute', left, top: 11, width, height: 36, borderRadius: 7, background: `linear-gradient(90deg, ${color.background} 0%, ${color.background}dd 100%)`, border: `1px solid ${color.border}`, boxShadow: `0 0 14px ${color.background}35`, cursor: dragState ? 'grabbing' : 'grab', overflow: 'hidden', userSelect: 'none' }}>
                            <div style={{ position: 'absolute', inset: 0, width: `${progress}%`, background: 'rgba(255,255,255,0.18)' }} />
                            <div onMouseDown={event => handleMouseDown(event, task, 'start')} style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 6, cursor: 'ew-resize', background: 'rgba(255,255,255,0.24)' }} />
                            <div onMouseDown={event => handleMouseDown(event, task, 'end')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 6, cursor: 'ew-resize', background: 'rgba(255,255,255,0.24)' }} />
                            <div style={{ position: 'relative', zIndex: 1, height: '100%', padding: '4px 8px 3px 10px', minWidth: 0 }}>
                              <div style={{ color: '#f8fafc', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: '14px' }}>{task.name}</div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#dbeafe', opacity: 0.92, marginTop: 3, whiteSpace: 'nowrap' }}>
                                <MoveHorizontal size={10} />
                                <span>{formatTimeLabel(taskTime.start)} - {formatTimeLabel(taskTime.end)}</span>
                                <span>{progress}%</span>
                                <span>{task.status || '-'}</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {tooltip && <TaskTooltip tooltip={tooltip} />}
    </div>
  );
}

function StateMessage({ icon, title, text, danger }) {
  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 8, background: 'rgba(15,23,42,0.62)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderRadius: 10, border: `1px solid ${danger ? 'rgba(239,68,68,0.35)' : 'rgba(59,130,246,0.25)'}`, background: 'rgba(15,23,42,0.94)', boxShadow: '0 12px 32px rgba(0,0,0,0.35)', color: danger ? '#fca5a5' : '#bfdbfe' }}>
        {icon}
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>{title}</div>
          <div style={{ fontSize: 11, color: danger ? '#fecaca' : '#94a3b8', marginTop: 3 }}>{text}</div>
        </div>
      </div>
    </div>
  );
}

function TaskTooltip({ tooltip }) {
  const { task, x, y } = tooltip;
  const items = [
    ['任务名称', task.name],
    ['开始时间', formatDateTime(task.start)],
    ['结束时间', formatDateTime(task.end)],
    ['进度', `${getProgressValue(task.progress)}%`],
    ['状态', task.status || '-'],
    ['工单ID', task.work_order_id || '-'],
    ['产品ID', task.product_id || '-'],
    ['产品名称', task.product_name || '-'],
    ['工序名称', task.step_name || '-'],
    ['顺序号', task.sequence_no ?? '-'],
    ['计划数量', task.planned_quantity ?? '-'],
    ['机台名称', task.machine_name || '-'],
  ];

  return (
    <div style={{ position: 'fixed', left: x, top: y, zIndex: 10000, width: 310, padding: 12, borderRadius: 10, background: 'rgba(15,23,42,0.98)', border: '1px solid rgba(96,165,250,0.32)', boxShadow: '0 16px 42px rgba(0,0,0,0.48)', pointerEvents: 'none', color: '#cbd5e1' }}>
      <div style={{ color: '#f8fafc', fontWeight: 800, marginBottom: 8, fontSize: 13 }}>{task.id}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '72px minmax(0, 1fr)', gap: '5px 8px', fontSize: 11 }}>
        {items.map(([label, value]) => (
          <div key={label} style={{ display: 'contents' }}>
            <div style={{ color: '#64748b' }}>{label}</div>
            <div style={{ color: '#e2e8f0', wordBreak: 'break-all' }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const baseButton = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 5,
  height: 26,
  padding: '0 9px',
  borderRadius: 6,
  fontSize: 11,
  color: '#cbd5e1',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(148,163,184,0.18)',
  cursor: 'pointer',
};

const styles = {
  button: baseButton,
  activeButton: {
    ...baseButton,
    color: '#dbeafe',
    background: 'rgba(37,99,235,0.34)',
    border: '1px solid rgba(96,165,250,0.52)',
    boxShadow: '0 0 12px rgba(37,99,235,0.24)',
  },
  iconButton: {
    ...baseButton,
    width: 26,
    padding: 0,
  },
  dateInput: {
    height: 26,
    padding: '0 8px',
    borderRadius: 6,
    color: '#dbeafe',
    colorScheme: 'dark',
    background: 'rgba(15,23,42,0.82)',
    border: '1px solid rgba(96,165,250,0.35)',
    fontSize: 11,
    outline: 'none',
  },
};
