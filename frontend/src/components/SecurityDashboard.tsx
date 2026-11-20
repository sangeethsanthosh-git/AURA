import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Lock,
  HardDrive,
  Globe,
  Radio,
  CheckCircle2,
  RefreshCw,
  PowerOff,
} from 'lucide-react';

interface SecurityStatus {
  policy: string;
  emergency_stop: {
    active: boolean;
    status: string;
  };
  process_isolation: {
    active: boolean;
    mechanism: string;
    active_processes: number;
  };
  filesystem_guard: {
    enforced: boolean;
    allowed_roots: string[];
    backup_directory: string;
    traversal_protection: boolean;
  };
  network_guard: {
    ssrf_defense_active: boolean;
    blocked_ip_ranges: string[];
    max_download_mb: number;
    blocked_extensions: string[];
  };
  prompt_guard: {
    dual_zone_cognitive_provenance: boolean;
    injection_patterns_loaded: number;
  };
  secret_store: {
    isolated_credentials_path: string;
    log_redaction_active: boolean;
  };
  pending_approvals_count: number;
  audit_statistics: {
    total_events: number;
    granted_count: number;
    blocked_count: number;
    checkpoints_count: number;
    log_path: string;
  };
}

interface PendingApproval {
  id: string;
  action_name: string;
  risk_level: string;
  target: string;
  preview_details: Record<string, any>;
  requested_at: string;
  expires_at: string;
  status: string;
}

interface AuditEvent {
  timestamp: string;
  event_type: string;
  risk_level: string;
  target: string;
  decision: string;
  reason: string;
  provenance: string;
  details: Record<string, any>;
}

interface SecurityDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SecurityDashboard: React.FC<SecurityDashboardProps> = ({ isOpen, onClose }) => {
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'checkpoints' | 'audit'>('overview');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, pendingRes, auditRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/api/security/status').then((r) => r.json()),
        fetch('http://127.0.0.1:8000/api/security/pending-approvals').then((r) => r.json()),
        fetch('http://127.0.0.1:8000/api/security/audit-events?limit=50').then((r) => r.json()),
      ]);
      setStatus(statusRes);
      setPendingApprovals(pendingRes.pending_approvals || []);
      setAuditEvents(auditRes.events || []);
    } catch (e) {
      console.error('Failed to load security status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchData();
      const interval = setInterval(fetchData, 4000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleApprove = async (approvalId: string) => {
    try {
      setActionLoading(approvalId);
      const res = await fetch(`http://127.0.0.1:8000/api/security/approve/${approvalId}`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error('Approval failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    try {
      setActionLoading(approvalId);
      const res = await fetch(`http://127.0.0.1:8000/api/security/reject/${approvalId}`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error('Rejection failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleEmergencyStop = async () => {
    if (!status) return;
    try {
      setActionLoading('emergency_stop');
      const endpoint = status.emergency_stop.active
        ? 'http://127.0.0.1:8000/api/security/emergency-reset'
        : 'http://127.0.0.1:8000/api/security/emergency-stop';
      await fetch(endpoint, { method: 'POST' });
      await fetchData();
    } catch (err) {
      console.error('Emergency stop toggle failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const isEmergencyStopActive = status?.emergency_stop.active ?? false;

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        className="security-dashboard-window"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '950px',
          maxWidth: '96vw',
          maxHeight: '90vh',
          backgroundColor: '#11141a',
          color: '#f0f2f5',
          borderRadius: '16px',
          border: isEmergencyStopActive ? '2px solid #ef4444' : '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: isEmergencyStopActive
            ? '0 0 40px rgba(239, 68, 68, 0.35)'
            : '0 25px 60px rgba(0, 0, 0, 0.55)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        {/* Top Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: isEmergencyStopActive
              ? 'linear-gradient(90deg, #3f1010 0%, #1a1010 100%)'
              : 'linear-gradient(90deg, #161b24 0%, #11141a 100%)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: isEmergencyStopActive ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: isEmergencyStopActive
                  ? '1px solid rgba(239, 68, 68, 0.5)'
                  : '1px solid rgba(16, 185, 129, 0.3)',
              }}
            >
              {isEmergencyStopActive ? (
                <ShieldAlert size={22} color="#ef4444" />
              ) : (
                <ShieldCheck size={22} color="#10b981" />
              )}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '17px', fontWeight: 700, letterSpacing: '-0.01em' }}>
                  AURA Zero-Trust Security Dashboard
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '20px',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    color: '#94a3b8',
                    letterSpacing: '0.05em',
                  }}
                >
                  {status?.policy || 'POLICY v1.0'}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                Deterministic enforcement, Windows Job Object process containment, and multi-tier checkpoints
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Global Emergency Stop Kill Switch Button */}
            <button
              onClick={handleToggleEmergencyStop}
              disabled={actionLoading === 'emergency_stop'}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                border: 'none',
                backgroundColor: isEmergencyStopActive ? '#f59e0b' : '#ef4444',
                color: '#ffffff',
                boxShadow: isEmergencyStopActive
                  ? '0 0 16px rgba(245, 158, 11, 0.5)'
                  : '0 0 16px rgba(239, 68, 68, 0.4)',
              }}
              title={
                isEmergencyStopActive
                  ? 'Reset Emergency Stop to resume standard operation'
                  : 'Immediately kill all child processes, revoke pending actions, and halt pipelines'
              }
            >
              <PowerOff size={15} />
              <span>{isEmergencyStopActive ? 'RESET EMERGENCY STOP' : 'KILL SWITCH (EMERGENCY STOP)'}</span>
            </button>

            <button
              onClick={onClose}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                fontSize: '18px',
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Emergency Stop Active Warning Banner */}
        {isEmergencyStopActive && (
          <div
            style={{
              padding: '12px 24px',
              backgroundColor: '#7f1d1d',
              color: '#fef2f2',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '13px',
              fontWeight: 600,
              borderBottom: '1px solid #b91c1c',
            }}
          >
            <AlertTriangle size={18} color="#fca5a5" />
            <span>
              EMERGENCY LOCKDOWN ACTIVE: All child processes have been terminated, active approvals revoked, and
              speech/inference pipelines halted. Click "RESET EMERGENCY STOP" above to resume normal operations.
            </span>
          </div>
        )}

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            padding: '12px 24px 0 24px',
            gap: '8px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            backgroundColor: '#141820',
          }}
        >
          <button
            onClick={() => setActiveTab('overview')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: activeTab === 'overview' ? '#1a202c' : 'transparent',
              color: activeTab === 'overview' ? '#38bdf8' : '#94a3b8',
              borderBottom: activeTab === 'overview' ? '2px solid #38bdf8' : '2px solid transparent',
            }}
          >
            🛡️ Security Controls
          </button>
          <button
            onClick={() => setActiveTab('checkpoints')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: activeTab === 'checkpoints' ? '#1a202c' : 'transparent',
              color: activeTab === 'checkpoints' ? '#38bdf8' : '#94a3b8',
              borderBottom: activeTab === 'checkpoints' ? '2px solid #38bdf8' : '2px solid transparent',
            }}
          >
            <span>Pending Checkpoints</span>
            {pendingApprovals.length > 0 && (
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  backgroundColor: '#f59e0b',
                  color: '#000000',
                  borderRadius: '12px',
                  padding: '1px 7px',
                }}
              >
                {pendingApprovals.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: activeTab === 'audit' ? '#1a202c' : 'transparent',
              color: activeTab === 'audit' ? '#38bdf8' : '#94a3b8',
              borderBottom: activeTab === 'audit' ? '2px solid #38bdf8' : '2px solid transparent',
            }}
          >
            📜 Audit Log Stream ({auditEvents.length})
          </button>
          <div style={{ flex: 1 }} />
          <button
            onClick={fetchData}
            title="Refresh Security Status"
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '8px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {/* TAB 1: OVERVIEW & SUBSYSTEM STATUS */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Quick Status Stats Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
                <div
                  style={{
                    backgroundColor: '#161c26',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    Process Isolation
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                    Job Object Active
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    Kill-on-close & 2GB limit enforced
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: '#161c26',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    Filesystem Guard
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                    Strict Boundaries
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    Shadow backups active before write
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: '#161c26',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    SSRF & Network Defense
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                    Private IPs Blocked
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    Executable downloads restricted
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: '#161c26',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    Prompt Injection Guard
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                    Dual-Zone Defense
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    8 heuristic signatures active
                  </div>
                </div>
              </div>

              {/* Subsystems Detailed Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {/* Process Sandbox */}
                <div
                  style={{
                    backgroundColor: '#151922',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <HardDrive size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>OS-Level Process Isolation</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
                    <div>
                      • <strong>Mechanism:</strong> Windows Kernel Job Object
                    </div>
                    <div>
                      • <strong>Guarantees:</strong> JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000)
                    </div>
                    <div>
                      • <strong>Resource Cap:</strong> 2.0 GB virtual memory & max 8 child processes
                    </div>
                    <div>
                      • <strong>Shell Policy:</strong> strictly <code>shell=False</code> with vector arguments
                    </div>
                    <div>
                      • <strong>Environment:</strong> Sanitized (API keys, secrets & passwords stripped)
                    </div>
                  </div>
                </div>

                {/* Filesystem Guard */}
                <div
                  style={{
                    backgroundColor: '#151922',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Lock size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>Filesystem Protection</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
                    <div>
                      • <strong>Canonical Resolution:</strong> Path traversal (<code>..</code>) & NTFS ADS blocked
                    </div>
                    <div>
                      • <strong>Protected Zones:</strong> System32, Windows, .ssh, .aws, browser credential stores
                    </div>
                    <div>
                      • <strong>Shadow Backup:</strong> Pre-modification copy in <code>AppData/Local/AURA/backups</code>
                    </div>
                    <div>
                      • <strong>Authorized Roots:</strong> Project folder, Desktop, Downloads, Documents, Media
                    </div>
                  </div>
                </div>

                {/* Network & SSRF Guard */}
                <div
                  style={{
                    backgroundColor: '#151922',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Globe size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>Network & SSRF Guard</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
                    <div>
                      • <strong>SSRF Defense:</strong> Blocks 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8
                    </div>
                    <div>
                      • <strong>Metadata Protection:</strong> 169.254.169.254 (Cloud instance metadata) prohibited
                    </div>
                    <div>
                      • <strong>Download Size Cap:</strong> Enforces 100 MB hard ceiling on downloads
                    </div>
                    <div>
                      • <strong>Blocked Extensions:</strong> .exe, .msi, .bat, .cmd, .ps1, .vbs, .dll, .jar
                    </div>
                  </div>
                </div>

                {/* AI Prompt Injection Defense */}
                <div
                  style={{
                    backgroundColor: '#151922',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Radio size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>AI Prompt Injection Defense</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
                    <div>
                      • <strong>Dual-Zone Provenance:</strong> Separates <code>TRUSTED_USER</code> from external data
                    </div>
                    <div>
                      • <strong>Passive Isolation:</strong> Untrusted text wrapped in non-executable XML delimiters
                    </div>
                    <div>
                      • <strong>Pattern Neutralization:</strong> Redacts instruction overrides & jailbreak attempts
                    </div>
                    <div>
                      • <strong>Deterministic Gate:</strong> LLM can NEVER grant itself permissions or bypass policy
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: PENDING APPROVAL CHECKPOINTS */}
          {activeTab === 'checkpoints' && (
            <div>
              {pendingApprovals.length === 0 ? (
                <div
                  style={{
                    textAlign: 'center',
                    padding: '48px 24px',
                    backgroundColor: '#151922',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <CheckCircle2 size={40} color="#10b981" style={{ margin: '0 auto 12px auto' }} />
                  <div style={{ fontSize: '16px', fontWeight: 600 }}>No Pending Checkpoints</div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    All operations are verified and compliant with Zero-Trust policy.
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {pendingApprovals.map((approval) => (
                    <div
                      key={approval.id}
                      style={{
                        backgroundColor: '#161c26',
                        borderRadius: '12px',
                        border: '1px solid #f59e0b',
                        padding: '16px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: approval.risk_level.includes('3') ? '#ef4444' : '#f59e0b',
                              color: '#ffffff',
                            }}
                          >
                            {approval.risk_level}
                          </span>
                          <span style={{ fontSize: '15px', fontWeight: 600 }}>{approval.action_name}</span>
                        </div>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>ID: #{approval.id}</span>
                      </div>

                      <div style={{ fontSize: '13px', color: '#cbd5e1' }}>
                        <div>
                          <strong>Target:</strong> <code>{approval.target}</code>
                        </div>
                        {approval.preview_details?.reason && (
                          <div style={{ marginTop: '4px', color: '#94a3b8' }}>
                            <strong>Reason:</strong> {approval.preview_details.reason}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                        <button
                          onClick={() => handleReject(approval.id)}
                          disabled={actionLoading === approval.id}
                          style={{
                            padding: '7px 16px',
                            borderRadius: '6px',
                            backgroundColor: 'rgba(239, 68, 68, 0.15)',
                            border: '1px solid rgba(239, 68, 68, 0.4)',
                            color: '#f87171',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Deny Action
                        </button>
                        <button
                          onClick={() => handleApprove(approval.id)}
                          disabled={actionLoading === approval.id}
                          style={{
                            padding: '7px 16px',
                            borderRadius: '6px',
                            backgroundColor: '#10b981',
                            border: 'none',
                            color: '#ffffff',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Authorize Action
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AUDIT LOG STREAM */}
          {activeTab === 'audit' && (
            <div
              style={{
                backgroundColor: '#151922',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '130px 170px 100px 130px 1fr',
                  padding: '10px 16px',
                  backgroundColor: '#1a202c',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div>Timestamp</div>
                <div>Event Type</div>
                <div>Risk</div>
                <div>Decision</div>
                <div>Reason & Target</div>
              </div>

              <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
                {auditEvents.length === 0 ? (
                  <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                    No audit records captured yet.
                  </div>
                ) : (
                  auditEvents.map((ev, idx) => {
                    const isDenied = ev.decision === 'DENIED' || ev.decision === 'BLOCKED' || ev.decision === 'HALTED';
                    const isCheckpoint = ev.decision === 'REQUIRES_CONFIRMATION';
                    return (
                      <div
                        key={idx}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '130px 170px 100px 130px 1fr',
                          padding: '10px 16px',
                          fontSize: '12px',
                          borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                          backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.015)',
                        }}
                      >
                        <div style={{ color: '#64748b', fontSize: '11px' }}>
                          {ev.timestamp ? ev.timestamp.slice(11, 19) : '--:--:--'}
                        </div>
                        <div style={{ fontWeight: 600, color: '#e2e8f0' }}>{ev.event_type}</div>
                        <div>
                          <span
                            style={{
                              fontSize: '10px',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              backgroundColor:
                                ev.risk_level === 'CRITICAL'
                                  ? '#7f1d1d'
                                  : ev.risk_level === 'HIGH' || ev.risk_level === 'LEVEL_3_SENSITIVE'
                                  ? '#831843'
                                  : ev.risk_level === 'LEVEL_2_CONTROLLED'
                                  ? '#78350f'
                                  : '#14532d',
                              color: '#ffffff',
                              fontWeight: 600,
                            }}
                          >
                            {ev.risk_level}
                          </span>
                        </div>
                        <div>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 600,
                              color: isDenied ? '#ef4444' : isCheckpoint ? '#f59e0b' : '#10b981',
                            }}
                          >
                            {ev.decision}
                          </span>
                        </div>
                        <div style={{ color: '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <span style={{ color: '#94a3b8' }}>[{ev.target}]</span> {ev.reason}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SecurityDashboard;
