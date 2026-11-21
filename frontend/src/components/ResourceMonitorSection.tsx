import React, { useState, useEffect } from 'react';
import { Activity, Cpu, HardDrive, Trash2, RefreshCw, Eye, Zap, CheckCircle2, ShieldCheck } from 'lucide-react';

interface ResourceMetrics {
  ram: {
    process_mb: number;
    system_used_mb: number;
    system_total_mb: number;
    system_percent: number;
  };
  cpu: {
    process_percent: number;
    system_percent: number;
  };
  gpu: {
    available: boolean;
    device_name: string;
    allocated_mb: number;
    reserved_mb: number;
    total_mb: number;
    free_mb: number;
    vram_percent: number;
  };
  latency: {
    screenshot_capture_last_ms: number;
    screenshot_capture_avg_ms: number;
    ocr_last_ms: number;
    ocr_avg_ms: number;
  };
  cache: {
    entries_count: number;
    max_entries: number;
    estimated_memory_kb: number;
    hit_count: number;
    miss_count: number;
    hit_ratio: number;
    ttl_seconds: number;
  };
  temporary_storage: {
    temp_directory: string;
    file_count: number;
    size_kb: number;
  };
  models: {
    loaded_models: string[];
    count: number;
    has_vision_model_loaded: boolean;
  };
}

export const ResourceMonitorSection: React.FC = () => {
  const [metrics, setMetrics] = useState<ResourceMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/system/resource-metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (e) {
      console.debug('Failed to fetch resource metrics:', e);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleClearCache = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/perception/cache-clear', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Cleared ${data.cleared_entries || 0} perception entries.`);
        await fetchMetrics();
      }
    } catch (e) {
      setActionMessage('Failed to clear perception cache.');
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 3500);
    }
  };

  const handleCleanupTemp = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/perception/cleanup-temp', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Deleted ${data.deleted_files || 0} temporary screenshot files.`);
        await fetchMetrics();
      }
    } catch (e) {
      setActionMessage('Failed to clean up temporary files.');
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 3500);
    }
  };

  const handleUnloadModels = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/system/models/unload', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Unloaded ${data.count || 0} models from GPU VRAM.`);
        await fetchMetrics();
      }
    } catch (e) {
      setActionMessage('Failed to unload GPU models.');
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 3500);
    }
  };

  if (!metrics) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-[#8C7E75] gap-2">
        <RefreshCw className="animate-spin text-[#FF7E5F]" size={20} />
        <span className="text-xs">Loading resource telemetry...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto max-h-[360px] pr-1 luminous-scroller text-xs">
      {actionMessage && (
        <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-2 text-[11px] animate-in fade-in">
          <CheckCircle2 size={14} className="text-emerald-600 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Grid: RAM, CPU, VRAM */}
      <div className="grid grid-cols-3 gap-2">
        {/* RAM */}
        <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[#8C7E75]">
            <span className="flex items-center gap-1 font-medium text-[11px]">
              <HardDrive size={12} className="text-[#FF7E5F]" />
              RAM (Process)
            </span>
            <span className="font-semibold text-[#1F1C1A]">{metrics.ram.process_mb} MB</span>
          </div>
          <div className="w-full bg-black/[0.06] rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#FF7E5F] to-[#FF5436] h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, (metrics.ram.process_mb / 2048) * 100)}%` }}
            />
          </div>
          <span className="text-[10px] text-[#8C7E75]">System: {metrics.ram.system_percent}% used</span>
        </div>

        {/* CPU */}
        <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[#8C7E75]">
            <span className="flex items-center gap-1 font-medium text-[11px]">
              <Cpu size={12} className="text-[#FF7E5F]" />
              CPU Usage
            </span>
            <span className="font-semibold text-[#1F1C1A]">{metrics.cpu.system_percent}%</span>
          </div>
          <div className="w-full bg-black/[0.06] rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#FF7E5F] to-[#FF5436] h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, metrics.cpu.system_percent)}%` }}
            />
          </div>
          <span className="text-[10px] text-[#8C7E75]">AURA: {metrics.cpu.process_percent}% load</span>
        </div>

        {/* GPU VRAM */}
        <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[#8C7E75]">
            <span className="flex items-center gap-1 font-medium text-[11px]">
              <Zap size={12} className="text-[#FF7E5F]" />
              GPU VRAM
            </span>
            <span className="font-semibold text-[#1F1C1A]">
              {metrics.gpu.available ? `${metrics.gpu.reserved_mb} MB` : 'N/A'}
            </span>
          </div>
          <div className="w-full bg-black/[0.06] rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                metrics.gpu.vram_percent > 80 ? 'bg-rose-500' : 'bg-gradient-to-r from-emerald-500 to-teal-500'
              }`}
              style={{ width: `${Math.min(100, metrics.gpu.vram_percent)}%` }}
            />
          </div>
          <span className="text-[10px] text-[#8C7E75] truncate" title={metrics.gpu.device_name}>
            {metrics.gpu.available ? `${metrics.gpu.free_mb} MB free` : 'Integrated'}
          </span>
        </div>
      </div>

      {/* Latency & Perception Performance */}
      <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex flex-col gap-2">
        <span className="text-[11px] font-semibold text-[#1F1C1A] flex items-center gap-1.5">
          <Activity size={13} className="text-[#FF7E5F]" />
          Perception & Processing Latencies
        </span>
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-black/[0.04]">
            <span className="text-[#7A6E64]">Screen Capture</span>
            <span className="font-semibold text-[#1F1C1A]">
              {metrics.latency.screenshot_capture_last_ms > 0 ? `${metrics.latency.screenshot_capture_last_ms}ms` : 'Idle'}
            </span>
          </div>
          <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-black/[0.04]">
            <span className="text-[#7A6E64]">Windows Media OCR</span>
            <span className="font-semibold text-[#1F1C1A]">
              {metrics.latency.ocr_last_ms > 0 ? `${metrics.latency.ocr_last_ms}ms` : 'Cached / 0ms'}
            </span>
          </div>
        </div>
      </div>

      {/* Perception Cache & Storage Stats */}
      <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#1F1C1A] flex items-center gap-1.5">
            <Eye size={13} className="text-[#FF7E5F]" />
            Perception Cache & Temporary Files
          </span>
          <span className="text-[10px] text-[#8C7E75]">TTL: {metrics.cache.ttl_seconds}s</span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-[11px]">
          <div className="p-2 rounded-xl bg-white border border-black/[0.04] flex flex-col">
            <span className="text-[#8C7E75] text-[10px]">Cached Screens</span>
            <span className="font-semibold text-[#1F1C1A]">
              {metrics.cache.entries_count} / {metrics.cache.max_entries}
            </span>
          </div>
          <div className="p-2 rounded-xl bg-white border border-black/[0.04] flex flex-col">
            <span className="text-[#8C7E75] text-[10px]">Hit Ratio</span>
            <span className="font-semibold text-emerald-600">
              {Math.round(metrics.cache.hit_ratio * 100)}% ({metrics.cache.hit_count} hits)
            </span>
          </div>
          <div className="p-2 rounded-xl bg-white border border-black/[0.04] flex flex-col">
            <span className="text-[#8C7E75] text-[10px]">Temp Storage</span>
            <span className="font-semibold text-[#1F1C1A]">
              {metrics.temporary_storage.file_count} files ({metrics.temporary_storage.size_kb} KB)
            </span>
          </div>
        </div>
      </div>

      {/* Active Models in VRAM */}
      <div className="p-3 rounded-2xl bg-black/[0.02] border border-black/[0.06] flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#1F1C1A] flex items-center gap-1.5">
            <ShieldCheck size={13} className="text-emerald-600" />
            Active GPU/VRAM Models
          </span>
          <span className="text-[10px] text-[#8C7E75]">
            {metrics.models.count === 0
              ? 'No models idle in VRAM (Clean)'
              : metrics.models.loaded_models.join(', ')}
          </span>
        </div>
        <button
          type="button"
          onClick={handleUnloadModels}
          disabled={loading || metrics.models.count === 0}
          className="px-2.5 py-1.5 rounded-xl bg-black/[0.04] hover:bg-black/[0.08] text-[#1F1C1A] text-[11px] font-medium transition cursor-pointer disabled:opacity-40"
        >
          Unload VRAM
        </button>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          type="button"
          onClick={handleClearCache}
          disabled={loading || metrics.cache.entries_count === 0}
          className="w-full py-2 px-3 rounded-xl bg-black/[0.04] hover:bg-black/[0.08] text-[#1F1C1A] font-medium text-[11px] flex items-center justify-center gap-1.5 transition cursor-pointer disabled:opacity-40"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Clear Perception Cache
        </button>
        <button
          type="button"
          onClick={handleCleanupTemp}
          disabled={loading || metrics.temporary_storage.file_count === 0}
          className="w-full py-2 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-medium text-[11px] flex items-center justify-center gap-1.5 transition cursor-pointer disabled:opacity-40"
        >
          <Trash2 size={12} />
          Purge Temp Screenshots
        </button>
      </div>
    </div>
  );
};
