import React, { useState, useEffect } from 'react';
import { useApi } from './contexts/ApiContext';
import { Table, WaitlistEntry, SMSLog } from './types';
import { 
  Users, 
  UserPlus, 
  Bell, 
  X, 
  Utensils, 
  MessageSquare, 
  Clock, 
  Check, 
  AlertCircle,
  RefreshCw
} from 'lucide-react';

export default function App() {
  const api = useApi();

  const [tables, setTables] = useState<Table[]>([]);
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [smsLogs, setSmsLogs] = useState<SMSLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [guestName, setGuestName] = useState('');
  const [partySize, setPartySize] = useState('2');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Filter state for Waitlist
  const [showAllWaitlist, setShowAllWaitlist] = useState(false);

  // Load and subscribe to updates
  const loadData = async (showSpinner = false) => {
    if (showSpinner) setIsLoading(true);
    try {
      const [fetchedTables, fetchedWaitlist, fetchedLogs] = await Promise.all([
        api.getTables(),
        api.getWaitlist(),
        api.getSmsLogs(),
      ]);
      setTables(fetchedTables);
      setWaitlist(fetchedWaitlist);
      setSmsLogs(fetchedLogs);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load restaurant waitlist data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);

    // Subscribe to real-time updates from the service
    const unsubscribe = api.subscribe((event) => {
      console.log(`Real-time update received: ${event}`);
      loadData(false);
    });

    return () => {
      unsubscribe();
    };
  }, [api]);

  // Form Submission
  const handleJoinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const nameTrimmed = guestName.trim();
    const sizeParsed = parseInt(partySize, 10);
    const phoneTrimmed = phoneNumber.trim();

    if (!nameTrimmed) {
      setFormError('Guest name is required.');
      return;
    }
    if (isNaN(sizeParsed) || sizeParsed <= 0) {
      setFormError('Party size must be a positive number.');
      return;
    }
    if (!phoneTrimmed) {
      setFormError('Phone number is required.');
      return;
    }

    try {
      setIsSubmitting(true);
      await api.joinWaitlist({
        guest_name: nameTrimmed,
        party_size: sizeParsed,
        phone_number: phoneTrimmed,
      });
      // Reset form
      setGuestName('');
      setPartySize('2');
      setPhoneNumber('');
    } catch (err: any) {
      setFormError(err.message || 'Error joining the waitlist.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Actions
  const handleNotify = async (partyId: number) => {
    try {
      await api.notifyParty(partyId);
    } catch (err: any) {
      alert(err.message || 'Failed to notify party.');
    }
  };

  const handleCancel = async (partyId: number) => {
    if (window.confirm('Are you sure you want to cancel this reservation?')) {
      try {
        await api.cancelParty(partyId);
      } catch (err: any) {
        alert(err.message || 'Failed to cancel party.');
      }
    }
  };

  const handleSeat = async (partyId: number, tableId: number) => {
    if (!tableId) return;
    try {
      await api.seatParty(partyId, tableId);
    } catch (err: any) {
      alert(err.message || 'Failed to seat party.');
    }
  };

  const handleClearTable = async (tableId: number) => {
    try {
      await api.clearTable(tableId);
    } catch (err: any) {
      alert(err.message || 'Failed to update table status.');
    }
  };

  // Time Formatter for elapsed minutes
  const getWaitTimeText = (joinedAtString: string) => {
    const joined = new Date(joinedAtString);
    const now = new Date();
    const diffMs = now.getTime() - joined.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just joined';
    return `${diffMins}m waiting`;
  };

  // Filtered waitlist based on toggle
  const activeWaitlist = waitlist.filter(entry => 
    showAllWaitlist ? true : (entry.status === 'WAITING' || entry.status === 'NOTIFIED')
  );

  // Helper to find name of seated party at a table
  const getSeatedPartyName = (table: Table) => {
    if (!table.current_party_id) return null;
    const party = waitlist.find(p => p.id === table.current_party_id);
    return party ? `${party.guest_name} (Party of ${party.party_size})` : 'Seated Guest';
  };

  // Count analytics for status dashboard
  const stats = {
    totalWaiting: waitlist.filter(w => w.status === 'WAITING' || w.status === 'NOTIFIED').length,
    availableTables: tables.filter(t => t.status === 'AVAILABLE').length,
    occupiedTables: tables.filter(t => t.status === 'OCCUPIED').length,
    dirtyTables: tables.filter(t => t.status === 'DIRTY').length,
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Sticky App Header */}
      <header className="app-header">
        <div className="app-title-group">
          <span className="app-logo">🍽️</span>
          <div>
            <h1 className="app-title">L'Étoile Host Stand</h1>
            <p className="app-subtitle">Waitlist & Table Management Dashboard</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => loadData(true)} 
            style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
            title="Refresh dashboard state"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          
          <div className="system-status">
            <span className="status-dot"></span>
            <span>Live Sync Connected</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      {isLoading && tables.length === 0 ? (
        <div className="spinner-container" style={{ flex: 1 }}>
          <div className="spinner"></div>
        </div>
      ) : error ? (
        <div style={{ padding: '3rem 1.5rem', textAlign: 'center', maxWidth: '600px', margin: '0 auto' }}>
          <AlertCircle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>Connection Error</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
          <button className="btn btn-primary" onClick={() => loadData(true)}>Retry Connection</button>
        </div>
      ) : (
        <main style={{ flex: 1 }}>
          <div className="dashboard">
            
            {/* Column 1: Waitlist Panel */}
            <section className="panel">
              <div className="panel-header">
                <h2 className="panel-title">
                  <Users size={20} color="var(--primary)" />
                  Guest Waitlist
                  <span className="panel-badge">{stats.totalWaiting} waiting</span>
                </h2>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={showAllWaitlist} 
                      onChange={(e) => setShowAllWaitlist(e.target.checked)}
                      style={{ marginRight: '0.25rem' }}
                    />
                    Show Seated/Cancelled
                  </label>
                </div>
              </div>

              {/* Add New Guest Form */}
              <form onSubmit={handleJoinWaitlist} className="guest-form">
                <h3 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <UserPlus size={16} /> Add Guest to Waitlist
                </h3>
                
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="guest-name">Guest Name</label>
                    <input
                      id="guest-name"
                      type="text"
                      className="form-control"
                      placeholder="e.g. Eleanor Vance"
                      value={guestName}
                      onChange={(e) => setGuestName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="party-size">Party Size</label>
                    <input
                      id="party-size"
                      type="number"
                      min="1"
                      max="20"
                      className="form-control"
                      value={partySize}
                      onChange={(e) => setPartySize(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="phone-number">Mobile Phone (for SMS Notification)</label>
                  <input
                    id="phone-number"
                    type="tel"
                    className="form-control"
                    placeholder="e.g. 555-0199"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    required
                  />
                </div>

                {formError && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#b91c1c', fontSize: '0.75rem', fontWeight: 500 }}>
                    <AlertCircle size={14} /> {formError}
                  </div>
                )}

                <button type="submit" className="btn btn-primary" disabled={isSubmitting} style={{ alignSelf: 'flex-start', marginTop: '0.25rem' }}>
                  {isSubmitting ? 'Adding...' : 'Add to Queue'}
                </button>
              </form>

              {/* Waitlist Queue Container */}
              <div className="waitlist-container">
                {activeWaitlist.length === 0 ? (
                  <div className="waitlist-empty">
                    <Users size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                    <p>No active guests on the waitlist.</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Use the form above to add a guest.</p>
                  </div>
                ) : (
                  activeWaitlist.map((entry) => {
                    const isWaiting = entry.status === 'WAITING';
                    const isNotified = entry.status === 'NOTIFIED';
                    const isSeated = entry.status === 'SEATED';
                    const isCancelled = entry.status === 'CANCELLED';

                    // Filter available tables that can fit this party
                    const viableTables = tables.filter(
                      (t) => t.status === 'AVAILABLE' && t.capacity >= entry.party_size
                    );

                    return (
                      <div 
                        key={entry.id} 
                        className={`waitlist-card ${isNotified ? 'notified' : ''}`}
                        style={{ 
                          opacity: (isSeated || isCancelled) ? 0.6 : 1,
                          borderLeft: isSeated ? '4px solid #94a3b8' : isCancelled ? '4px solid #ef4444' : undefined
                        }}
                      >
                        <div className="guest-info">
                          <div className="guest-meta">
                            <span className="guest-name">{entry.guest_name}</span>
                            <span className="party-badge">
                              <Users size={12} style={{ verticalAlign: 'text-bottom', marginRight: '0.25rem' }} />
                              Party of {entry.party_size}
                            </span>
                            <span className={`status-badge ${entry.status.toLowerCase()}`}>
                              {entry.status}
                            </span>
                          </div>
                          
                          <div className="guest-subtext">
                            <span>📱 {entry.phone_number}</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.125rem' }}>
                              <Clock size={11} />
                              {getWaitTimeText(entry.joined_at)}
                              {entry.notified_at && ` • Notified ${new Date(entry.notified_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`}
                              {entry.seated_at && ` • Seated ${new Date(entry.seated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`}
                            </span>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="card-actions">
                          {(isWaiting || isNotified) && (
                            <>
                              {isWaiting && (
                                <button 
                                  className="btn btn-secondary" 
                                  onClick={() => handleNotify(entry.id)}
                                  title="Send ready SMS notification"
                                  style={{ padding: '0.375rem 0.5rem', fontSize: '0.75rem' }}
                                >
                                  <Bell size={14} /> Notify
                                </button>
                              )}
                              
                              {/* Seating Dropdown Action */}
                              <div className="select-wrapper">
                                <select 
                                  className="select-control"
                                  value=""
                                  onChange={(e) => handleSeat(entry.id, parseInt(e.target.value, 10))}
                                >
                                  <option value="" disabled>Seat Table...</option>
                                  {viableTables.length === 0 ? (
                                    <option disabled>No available tables fit size {entry.party_size}</option>
                                  ) : (
                                    viableTables.map(t => (
                                      <option key={t.id} value={t.id}>
                                        {t.name} (Cap: {t.capacity})
                                      </option>
                                    ))
                                  )}
                                </select>
                                <span className="select-arrow">▼</span>
                              </div>

                              <button 
                                className="btn btn-secondary" 
                                onClick={() => handleCancel(entry.id)}
                                title="Cancel reservation"
                                style={{ padding: '0.375rem', color: '#ef4444' }}
                              >
                                <X size={14} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </section>

            {/* Column 2: Tables Floor Plan */}
            <section className="panel">
              <div className="panel-header">
                <h2 className="panel-title">
                  <Utensils size={20} color="var(--primary)" />
                  Restaurant Floor Layout
                </h2>
                
                <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', fontWeight: 600 }}>
                  <span style={{ color: 'var(--status-available-text)', backgroundColor: 'var(--status-available-bg)', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', border: '1px solid var(--status-available-border)' }}>
                    {stats.availableTables} Avail
                  </span>
                  <span style={{ color: 'var(--status-occupied-text)', backgroundColor: 'var(--status-occupied-bg)', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', border: '1px solid var(--status-occupied-border)' }}>
                    {stats.occupiedTables} Occupied
                  </span>
                  <span style={{ color: 'var(--status-dirty-text)', backgroundColor: 'var(--status-dirty-bg)', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', border: '1px solid var(--status-dirty-border)' }}>
                    {stats.dirtyTables} Dirty
                  </span>
                </div>
              </div>

              {/* Table Grid Floor Plan */}
              <div className="tables-grid">
                {tables.map((table) => {
                  const isAvailable = table.status === 'AVAILABLE';
                  const isOccupied = table.status === 'OCCUPIED';
                  const isDirty = table.status === 'DIRTY';

                  const seatedInfo = getSeatedPartyName(table);

                  return (
                    <div 
                      key={table.id} 
                      className={`table-card ${table.status.toLowerCase()}`}
                    >
                      <div className="table-info">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span className="table-name">{table.name}</span>
                          <span className="table-capacity">Cap: {table.capacity}</span>
                        </div>
                        
                        <span className="table-status-label">{table.status}</span>
                        
                        {isOccupied && seatedInfo && (
                          <div className="table-party-info" style={{ marginTop: '0.5rem' }}>
                            👤 {seatedInfo}
                          </div>
                        )}
                      </div>

                      {/* Action buttons inside table card */}
                      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column' }}>
                        {isOccupied && (
                          <button 
                            className="btn btn-secondary" 
                            onClick={() => handleClearTable(table.id)}
                            style={{ width: '100%', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          >
                            Mark Dirty
                          </button>
                        )}
                        {isDirty && (
                          <button 
                            className="btn btn-primary" 
                            onClick={() => handleClearTable(table.id)}
                            style={{ 
                              width: '100%', 
                              fontSize: '0.75rem', 
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#10b981',
                              borderColor: '#10b981'
                            }}
                          >
                            <Check size={12} style={{ marginRight: '0.125rem' }} /> Clear & Ready
                          </button>
                        )}
                        {isAvailable && (
                          <span style={{ 
                            fontSize: '0.75rem', 
                            textAlign: 'center', 
                            color: 'var(--status-available-text)', 
                            fontWeight: 600,
                            padding: '0.25rem 0'
                          }}>
                            Ready to Seat
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          {/* SMS History Panel */}
          <section className="sms-section">
            <div className="panel" style={{ minHeight: 'auto', gap: '0.75rem' }}>
              <div className="panel-header" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                <h2 className="panel-title" style={{ fontSize: '1rem' }}>
                  <MessageSquare size={18} color="var(--primary)" />
                  Sent Notifications Logs (SMS Simulator)
                </h2>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Real-time updates as SMS text messages are pushed</span>
              </div>

              <div className="sms-logs-container">
                {smsLogs.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    No SMS notifications sent yet.
                  </div>
                ) : (
                  [...smsLogs].reverse().map((log) => (
                    <div key={log.id} className="sms-log-item">
                      <span className="sms-log-text">
                        <strong>{log.phone_number}:</strong> {log.message}
                      </span>
                      <span className="sms-log-time">
                        {new Date(log.sent_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>
        </main>
      )}

      {/* Modern Compact Footer */}
      <footer style={{ 
        textAlign: 'center', 
        padding: '1rem', 
        fontSize: '0.75rem', 
        color: 'var(--text-muted)', 
        borderTop: '1px solid var(--border-color)',
        backgroundColor: '#ffffff'
      }}>
        L'Étoile Host Management System. Powered by React, Vite and Tailwind-free CSS.
      </footer>
    </div>
  );
}
