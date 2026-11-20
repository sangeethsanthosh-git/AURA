import React, { useState, useEffect } from 'react';
import { Mail, CheckCircle2, AlertCircle, RefreshCw, Send, Clock, Key, ShieldCheck } from 'lucide-react';

interface EmailStatus {
  is_connected: boolean;
  connected_account?: string;
  destination_email?: string;
  notifications_enabled: boolean;
  daily_summary_enabled: boolean;
  daily_summary_time: string;
  has_client_credentials: boolean;
}

interface EmailLog {
  id: number;
  recipient: string;
  subject: string;
  status: string;
  error_message?: string;
  sent_at: number;
}

export const EmailNotificationsSection: React.FC = () => {
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [destinationEmail, setDestinationEmail] = useState('');
  const [dailySummaryEnabled, setDailySummaryEnabled] = useState(false);
  const [dailySummaryTime, setDailySummaryTime] = useState('08:00');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  // Advanced OAuth Credentials
  const [showCreds, setShowCreds] = useState(false);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');

  // Status banners & feedback
  const [loading, setLoading] = useState(false);
  const [testSending, setTestSending] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [logs, setLogs] = useState<EmailLog[]>([]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/status');
      if (res.ok) {
        const data: EmailStatus = await res.json();
        setStatus(data);
        setDestinationEmail(data.destination_email || '');
        setDailySummaryEnabled(data.daily_summary_enabled);
        setDailySummaryTime(data.daily_summary_time || '08:00');
        setNotificationsEnabled(data.notifications_enabled);
      }
    } catch (e) {
      console.error('Failed to load email status:', e);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/history?limit=5');
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (e) {
      console.error('Failed to load email logs:', e);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchLogs();

    const handleOAuthMsg = (event: MessageEvent) => {
      if (event.data?.type === 'GMAIL_OAUTH_SUCCESS') {
        fetchStatus();
        setMessage({ text: 'Gmail connected successfully!', type: 'success' });
      }
    };
    window.addEventListener('message', handleOAuthMsg);
    return () => window.removeEventListener('message', handleOAuthMsg);
  }, []);

  const handleSaveSettings = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination_email: destinationEmail,
          notifications_enabled: notificationsEnabled,
          daily_summary_enabled: dailySummaryEnabled,
          daily_summary_time: dailySummaryTime,
        }),
      });
      if (res.ok) {
        setMessage({ text: 'Email settings saved successfully.', type: 'success' });
        fetchStatus();
      } else {
        const err = await res.json();
        setMessage({ text: err.detail || 'Failed to save settings.', type: 'error' });
      }
    } catch (e) {
      setMessage({ text: 'Network error saving settings.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCredentials = async () => {
    if (!clientId.trim() || !clientSecret.trim()) {
      setMessage({ text: 'Please enter both Client ID and Client Secret.', type: 'error' });
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
      });
      if (res.ok) {
        setMessage({ text: 'OAuth credentials securely stored in SecretStore.', type: 'success' });
        setShowCreds(false);
        fetchStatus();
      } else {
        const err = await res.json();
        setMessage({ text: err.detail || 'Failed to save credentials.', type: 'error' });
      }
    } catch (e) {
      setMessage({ text: 'Error saving OAuth credentials.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleConnectGmail = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/oauth/auth-url');
      const data = await res.json();
      if (res.ok && data.auth_url) {
        window.open(data.auth_url, '_blank', 'width=520,height=640');
      } else {
        setMessage({ text: data.detail || 'Could not generate OAuth consent URL. Check Client ID.', type: 'error' });
      }
    } catch (e) {
      setMessage({ text: 'Failed to initiate Gmail connection.', type: 'error' });
    }
  };

  const handleDisconnectGmail = async () => {
    if (!window.confirm('Disconnect your Gmail account from AURA?')) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/disconnect', { method: 'POST' });
      if (res.ok) {
        setMessage({ text: 'Gmail account disconnected.', type: 'success' });
        fetchStatus();
      }
    } catch (e) {
      setMessage({ text: 'Failed to disconnect Gmail.', type: 'error' });
    }
  };

  const handleSendTestEmail = async () => {
    setTestSending(true);
    setMessage(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/email/send-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: destinationEmail || undefined }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setMessage({ text: `Test email sent to ${data.recipient || destinationEmail}!`, type: 'success' });
        fetchLogs();
      } else {
        setMessage({ text: data.detail || data.error || 'Failed to send test email.', type: 'error' });
      }
    } catch (e) {
      setMessage({ text: 'Network error sending test email.', type: 'error' });
    } finally {
      setTestSending(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 overflow-y-auto max-h-[380px] pr-1 luminous-scroller text-[#1F1C1A]">
      {/* Header Info */}
      <div className="flex items-center justify-between px-1">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-[#9E9086]">
            Email & Scheduled Notifications
          </div>
          <div className="text-[12px] text-[#7A6E64]">
            Send important reminders, deadlines, and daily summaries via Gmail API
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-semibold text-[#7A6E64]">Master Switch</span>
          <input
            type="checkbox"
            checked={notificationsEnabled}
            onChange={(e) => setNotificationsEnabled(e.target.checked)}
            className="w-4 h-4 accent-[#D44726] rounded cursor-pointer"
          />
        </div>
      </div>

      {/* Message Banner */}
      {message && (
        <div
          className={`flex items-center gap-2 p-2 rounded-xl text-xs ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {message.type === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Gmail OAuth Connection Card */}
      <div className="bg-white/70 border border-black/[0.06] rounded-2xl p-3 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-[#D44726]/10 flex items-center justify-center text-[#D44726]">
              <Mail size={16} />
            </div>
            <div>
              <div className="text-[13px] font-semibold text-[#1F1C1A]">Gmail Integration</div>
              <div className="text-[11px] text-[#7A6E64]">Official Google API (gmail.send scope)</div>
            </div>
          </div>

          <div>
            {status?.is_connected ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-100 text-emerald-800">
                <CheckCircle2 size={12} /> Connected: {status.connected_account || 'Active'}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-gray-600">
                Not Connected
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 pt-1">
          {status?.is_connected ? (
            <button
              type="button"
              onClick={handleDisconnectGmail}
              className="px-3 py-1.5 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-xl transition cursor-pointer"
            >
              Disconnect Gmail
            </button>
          ) : (
            <button
              type="button"
              onClick={handleConnectGmail}
              className="px-3 py-1.5 text-xs font-semibold text-white bg-[#D44726] hover:bg-[#b8381a] rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer"
            >
              <Mail size={13} /> Connect Gmail Account
            </button>
          )}

          <button
            type="button"
            onClick={() => setShowCreds(!showCreds)}
            className="px-2.5 py-1.5 text-xs text-[#7A6E64] hover:text-[#1F1C1A] bg-black/[0.03] hover:bg-black/[0.06] rounded-xl transition flex items-center gap-1 cursor-pointer"
          >
            <Key size={12} /> {showCreds ? 'Hide API Keys' : 'OAuth Client Credentials'}
          </button>
        </div>

        {/* Collapsible Client Credentials form */}
        {showCreds && (
          <div className="bg-black/[0.02] border border-black/[0.04] rounded-xl p-2.5 flex flex-col gap-2 mt-1 text-xs">
            <div className="flex items-center gap-1 text-[#9E9086] font-medium">
              <ShieldCheck size={12} />
              <span>Google Cloud OAuth 2.0 Credentials (stored in Windows SecretStore)</span>
            </div>
            <input
              type="text"
              placeholder="Google Client ID (e.g. xxxxx.apps.googleusercontent.com)"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-black/[0.08] rounded-lg text-xs"
            />
            <input
              type="password"
              placeholder="Google Client Secret"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-black/[0.08] rounded-lg text-xs"
            />
            <button
              type="button"
              onClick={handleSaveCredentials}
              className="self-end px-3 py-1 bg-[#1F1C1A] text-white rounded-lg text-xs font-medium hover:bg-black cursor-pointer"
            >
              Save Credentials
            </button>
          </div>
        )}
      </div>

      {/* Destination Email Address */}
      <div className="bg-white/70 border border-black/[0.06] rounded-2xl p-3 flex flex-col gap-2">
        <label className="text-xs font-semibold text-[#1F1C1A]">Destination Email Address</label>
        <div className="flex items-center gap-2">
          <input
            type="email"
            placeholder="youremail@example.com"
            value={destinationEmail}
            onChange={(e) => setDestinationEmail(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-white border border-black/[0.08] rounded-xl text-xs text-[#1F1C1A] focus:outline-none focus:border-[#D44726]"
          />
          <button
            type="button"
            disabled={testSending || !destinationEmail}
            onClick={handleSendTestEmail}
            className="px-3 py-1.5 text-xs font-medium bg-black/[0.04] hover:bg-black/[0.08] text-[#1F1C1A] rounded-xl transition flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            {testSending ? <RefreshCw size={12} className="animate-spin" /> : <Send size={12} />}
            <span>Test Email</span>
          </button>
        </div>
      </div>

      {/* Daily Morning Summary */}
      <div className="bg-white/70 border border-black/[0.06] rounded-2xl p-3 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-[#D44726]" />
            <div>
              <div className="text-xs font-semibold text-[#1F1C1A]">Daily Morning Summary</div>
              <div className="text-[11px] text-[#7A6E64]">Digest of today's reminders, deadlines, and important notes</div>
            </div>
          </div>
          <input
            type="checkbox"
            checked={dailySummaryEnabled}
            onChange={(e) => setDailySummaryEnabled(e.target.checked)}
            className="w-4 h-4 accent-[#D44726] rounded cursor-pointer"
          />
        </div>

        {dailySummaryEnabled && (
          <div className="flex items-center gap-2 pt-1 border-t border-black/[0.04]">
            <span className="text-xs text-[#7A6E64]">Delivery Time:</span>
            <input
              type="time"
              value={dailySummaryTime}
              onChange={(e) => setDailySummaryTime(e.target.value)}
              className="px-2 py-1 bg-white border border-black/[0.08] rounded-lg text-xs"
            />
          </div>
        )}
      </div>

      {/* Recent Delivery History */}
      {logs.length > 0 && (
        <div className="bg-white/70 border border-black/[0.06] rounded-2xl p-3 flex flex-col gap-2 text-xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[#9E9086]">
            Recent Delivery History
          </div>
          <div className="flex flex-col gap-1.5">
            {logs.map((log) => (
              <div
                key={log.id}
                className="flex items-center justify-between p-1.5 bg-black/[0.02] rounded-lg border border-black/[0.03]"
              >
                <div className="flex flex-col">
                  <span className="font-medium text-[#1F1C1A] truncate max-w-[220px]">{log.subject}</span>
                  <span className="text-[10px] text-[#7A6E64]">{log.recipient}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                      log.status === 'sent'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {log.status}
                  </span>
                  <span className="text-[10px] text-[#9E9086]">
                    {new Date(log.sent_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Save Settings Button */}
      <div className="flex justify-end pt-1">
        <button
          type="button"
          disabled={loading}
          onClick={handleSaveSettings}
          className="px-4 py-1.5 text-xs font-semibold text-white bg-[#D44726] hover:bg-[#b8381a] rounded-xl shadow-xs transition flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
        >
          {loading && <RefreshCw size={12} className="animate-spin" />}
          <span>Save Email Preferences</span>
        </button>
      </div>
    </div>
  );
};
