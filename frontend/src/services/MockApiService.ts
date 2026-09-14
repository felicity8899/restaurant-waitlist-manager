import { ApiService } from './ApiService';
import { Table, WaitlistEntry, SMSLog } from '../types';

export class MockApiService implements ApiService {
  private tables: Table[] = [
    { id: 1, name: 'Table 1', capacity: 2, status: 'AVAILABLE', current_party_id: null },
    { id: 2, name: 'Table 2', capacity: 2, status: 'AVAILABLE', current_party_id: null },
    { id: 3, name: 'Table 3', capacity: 4, status: 'AVAILABLE', current_party_id: null },
    { id: 4, name: 'Table 4', capacity: 4, status: 'AVAILABLE', current_party_id: null },
    { id: 5, name: 'Booth 5', capacity: 6, status: 'AVAILABLE', current_party_id: null },
    { id: 6, name: 'Booth 6', capacity: 6, status: 'AVAILABLE', current_party_id: null },
    { id: 7, name: 'Table 7', capacity: 8, status: 'AVAILABLE', current_party_id: null },
  ];

  private waitlist: WaitlistEntry[] = [];
  private smsLogs: SMSLog[] = [];
  private subscribers: ((event: string) => void)[] = [];
  private nextWaitlistId = 1;
  private nextSmsId = 1;

  constructor() {
    // Add some initial waitlist and SMS logs for realistic demonstration
    this.joinWaitlist({ guest_name: 'John Doe', party_size: 2, phone_number: '555-0199' });
    this.joinWaitlist({ guest_name: 'Jane Smith', party_size: 4, phone_number: '555-0244' });
  }

  // Simulate minimal network latency
  private delay<T>(value: T, ms: number = 100): Promise<T> {
    return new Promise((resolve) => setTimeout(() => resolve(value), ms));
  }

  private broadcast(event: string) {
    this.subscribers.forEach((cb) => cb(event));
  }

  // --- Tables ---
  async getTables(): Promise<Table[]> {
    return this.delay([...this.tables]);
  }

  async clearTable(tableId: number): Promise<Table> {
    const tableIndex = this.tables.findIndex((t) => t.id === tableId);
    if (tableIndex === -1) {
      throw new Error(`Table with ID ${tableId} not found.`);
    }

    const table = this.tables[tableIndex];
    let newStatus = table.status;
    let currentPartyId = table.current_party_id;

    if (table.status === 'OCCUPIED') {
      newStatus = 'DIRTY';
      currentPartyId = null;
    } else if (table.status === 'DIRTY') {
      newStatus = 'AVAILABLE';
    }

    const updatedTable: Table = {
      ...table,
      status: newStatus,
      current_party_id: currentPartyId,
    };

    this.tables[tableIndex] = updatedTable;
    this.broadcast('TABLE_UPDATE');
    return this.delay(updatedTable);
  }

  // --- Waitlist ---
  async getWaitlist(): Promise<WaitlistEntry[]> {
    return this.delay([...this.waitlist]);
  }

  async joinWaitlist(guest: { guest_name: string; party_size: number; phone_number: string }): Promise<WaitlistEntry> {
    if (!guest.guest_name.trim()) {
      throw new Error('Guest name is required.');
    }
    if (guest.party_size <= 0) {
      throw new Error('Party size must be greater than zero.');
    }

    const newEntry: WaitlistEntry = {
      id: this.nextWaitlistId++,
      guest_name: guest.guest_name,
      party_size: guest.party_size,
      phone_number: guest.phone_number,
      status: 'WAITING',
      joined_at: new Date().toISOString(),
      notified_at: null,
      seated_at: null,
      table_id: null,
    };

    this.waitlist.push(newEntry);
    this.broadcast('QUEUE_UPDATE');
    return this.delay(newEntry);
  }

  async seatParty(partyId: number, tableId: number): Promise<{ party: WaitlistEntry; table: Table }> {
    const partyIndex = this.waitlist.findIndex((p) => p.id === partyId);
    if (partyIndex === -1) {
      throw new Error(`Party with ID ${partyId} not found.`);
    }

    const tableIndex = this.tables.findIndex((t) => t.id === tableId);
    if (tableIndex === -1) {
      throw new Error(`Table with ID ${tableId} not found.`);
    }

    const party = this.waitlist[partyIndex];
    const table = this.tables[tableIndex];

    if (party.status === 'SEATED' || party.status === 'CANCELLED') {
      throw new Error(`Cannot seat a party with status '${party.status}'.`);
    }

    if (table.status !== 'AVAILABLE') {
      throw new Error(`Table '${table.name}' is currently not available.`);
    }

    if (table.capacity < party.party_size) {
      throw new Error(`Table '${table.name}' capacity (${table.capacity}) is too small for party size (${party.party_size}).`);
    }

    const updatedParty: WaitlistEntry = {
      ...party,
      status: 'SEATED',
      table_id: tableId,
      seated_at: new Date().toISOString(),
    };

    const updatedTable: Table = {
      ...table,
      status: 'OCCUPIED',
      current_party_id: partyId,
    };

    this.waitlist[partyIndex] = updatedParty;
    this.tables[tableIndex] = updatedTable;

    this.broadcast('QUEUE_UPDATE');
    this.broadcast('TABLE_UPDATE');

    return this.delay({ party: updatedParty, table: updatedTable });
  }

  async notifyParty(partyId: number): Promise<WaitlistEntry> {
    const partyIndex = this.waitlist.findIndex((p) => p.id === partyId);
    if (partyIndex === -1) {
      throw new Error(`Party with ID ${partyId} not found.`);
    }

    const party = this.waitlist[partyIndex];
    if (party.status !== 'WAITING') {
      throw new Error(`Cannot notify a party with status '${party.status}'.`);
    }

    const updatedParty: WaitlistEntry = {
      ...party,
      status: 'NOTIFIED',
      notified_at: new Date().toISOString(),
    };

    const smsMessage = `Hi ${party.guest_name}, your table is ready! Please proceed to the host stand.`;
    const newSmsLog: SMSLog = {
      id: this.nextSmsId++,
      phone_number: party.phone_number,
      message: smsMessage,
      sent_at: new Date().toISOString(),
    };

    this.waitlist[partyIndex] = updatedParty;
    this.smsLogs.push(newSmsLog);

    this.broadcast('QUEUE_UPDATE');
    this.broadcast('SMS_UPDATE');

    return this.delay(updatedParty);
  }

  async cancelParty(partyId: number): Promise<WaitlistEntry> {
    const partyIndex = this.waitlist.findIndex((p) => p.id === partyId);
    if (partyIndex === -1) {
      throw new Error(`Party with ID ${partyId} not found.`);
    }

    const party = this.waitlist[partyIndex];
    let updatedTable: Table | null = null;

    if (party.status === 'SEATED' && party.table_id !== null) {
      const tableIndex = this.tables.findIndex((t) => t.id === party.table_id);
      if (tableIndex !== -1) {
        updatedTable = {
          ...this.tables[tableIndex],
          status: 'AVAILABLE',
          current_party_id: null,
        };
        this.tables[tableIndex] = updatedTable;
      }
    }

    const updatedParty: WaitlistEntry = {
      ...party,
      status: 'CANCELLED',
      table_id: null,
    };

    this.waitlist[partyIndex] = updatedParty;

    this.broadcast('QUEUE_UPDATE');
    if (updatedTable) {
      this.broadcast('TABLE_UPDATE');
    }

    return this.delay(updatedParty);
  }

  // --- SMS logs ---
  async getSmsLogs(): Promise<SMSLog[]> {
    return this.delay([...this.smsLogs]);
  }

  // --- Real-time subscription ---
  subscribe(callback: (event: string) => void): () => void {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter((cb) => cb !== callback);
    };
  }
}
