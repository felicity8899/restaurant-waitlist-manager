export type TableStatus = 'AVAILABLE' | 'OCCUPIED' | 'DIRTY';

export interface Table {
  id: number;
  name: string;
  capacity: number;
  status: TableStatus;
  current_party_id: number | null;
}

export type WaitlistStatus = 'WAITING' | 'NOTIFIED' | 'SEATED' | 'CANCELLED';

export interface WaitlistEntry {
  id: number;
  guest_name: string;
  party_size: number;
  phone_number: string;
  status: WaitlistStatus;
  joined_at: string;
  notified_at: string | null;
  seated_at: string | null;
  table_id: number | null;
}

export interface SMSLog {
  id: number;
  phone_number: string;
  message: string;
  sent_at: string;
}
