import { Table, WaitlistEntry, SMSLog } from '../types';

export interface ApiService {
  // Tables
  getTables(): Promise<Table[]>;
  clearTable(tableId: number): Promise<Table>;

  // Waitlist
  getWaitlist(): Promise<WaitlistEntry[]>;
  joinWaitlist(guest: { guest_name: string; party_size: number; phone_number: string }): Promise<WaitlistEntry>;
  seatParty(partyId: number, tableId: number): Promise<{ party: WaitlistEntry; table: Table }>;
  notifyParty(partyId: number): Promise<WaitlistEntry>;
  cancelParty(partyId: number): Promise<WaitlistEntry>;

  // SMS logs
  getSmsLogs(): Promise<SMSLog[]>;

  // Authentication
  login(pin: string): Promise<boolean>;
  logout(): void;
  isAuthenticated(): boolean;

  // Real-time synchronization subscription
  subscribe(callback: (event: string) => void): () => void;
}
