import { ApiService } from './ApiService';
import { Table, WaitlistEntry, SMSLog } from '../types';

export class FastApiService implements ApiService {
  private baseUrl: string;
  private wsUrl: string;
  private subscribers: ((event: string) => void)[] = [];
  private ws: WebSocket | null = null;
  private isConnecting = false;

  constructor() {
    // Determine backend URLs based on environment variables or defaults
    const backendHost = import.meta.env.VITE_API_HOST || `${window.location.hostname}:8000`;
    const isSsl = window.location.protocol === 'https:';
    this.baseUrl = `${isSsl ? 'https' : 'http'}://${backendHost}`;
    this.wsUrl = `${isSsl ? 'wss' : 'ws'}://${backendHost}/ws`;
    
    this.connectWebSocket();
  }

  private connectWebSocket() {
    if (this.ws || this.isConnecting) return;
    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        console.log('WebSocket connection established.');
      };

      this.ws.onmessage = (event) => {
        // Broadcast the websocket message to all service subscribers
        this.broadcast(event.data);
      };

      this.ws.onclose = () => {
        this.ws = null;
        this.isConnecting = false;
        console.log('WebSocket closed. Attempting reconnect in 3s...');
        setTimeout(() => this.connectWebSocket(), 3000);
      };

      this.ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        if (this.ws) {
          this.ws.close();
        }
      };
    } catch (err) {
      this.isConnecting = false;
      console.error('Failed to initiate WebSocket connection:', err);
      setTimeout(() => this.connectWebSocket(), 5000);
    }
  }

  private broadcast(event: string) {
    this.subscribers.forEach((cb) => cb(event));
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    };

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorText = await res.text();
      let errorMessage = `HTTP Error ${res.status}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorJson.message || errorMessage;
      } catch {
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }

    return res.json() as Promise<T>;
  }

  // --- Tables ---
  async getTables(): Promise<Table[]> {
    return this.request<Table[]>('/api/tables');
  }

  async clearTable(tableId: number): Promise<Table> {
    return this.request<Table>(`/api/tables/${tableId}/clear`, {
      method: 'POST',
    });
  }

  // --- Waitlist ---
  async getWaitlist(): Promise<WaitlistEntry[]> {
    return this.request<WaitlistEntry[]>('/api/waitlist');
  }

  async joinWaitlist(guest: { guest_name: string; party_size: number; phone_number: string }): Promise<WaitlistEntry> {
    return this.request<WaitlistEntry>('/api/waitlist', {
      method: 'POST',
      body: JSON.stringify(guest),
    });
  }

  async seatParty(partyId: number, tableId: number): Promise<{ party: WaitlistEntry; table: Table }> {
    return this.request<{ party: WaitlistEntry; table: Table }>(`/api/waitlist/${partyId}/seat`, {
      method: 'POST',
      body: JSON.stringify({ table_id: tableId }),
    });
  }

  async notifyParty(partyId: number): Promise<WaitlistEntry> {
    return this.request<WaitlistEntry>(`/api/waitlist/${partyId}/notify`, {
      method: 'POST',
    });
  }

  async cancelParty(partyId: number): Promise<WaitlistEntry> {
    return this.request<WaitlistEntry>(`/api/waitlist/${partyId}/cancel`, {
      method: 'POST',
    });
  }

  // --- SMS logs ---
  async getSmsLogs(): Promise<SMSLog[]> {
    return this.request<SMSLog[]>('/api/sms-logs');
  }

  // --- Real-time subscription ---
  subscribe(callback: (event: string) => void): () => void {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter((cb) => cb !== callback);
    };
  }
}
