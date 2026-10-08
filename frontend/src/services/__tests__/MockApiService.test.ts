import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MockApiService } from '../MockApiService';

describe('MockApiService', () => {
  let service: MockApiService;

  beforeEach(() => {
    // Note: MockApiService constructor auto-creates two guests (John Doe, Jane Smith)
    service = new MockApiService();
  });

  it('should initialize with default tables and seed guests', async () => {
    const tables = await service.getTables();
    expect(tables.length).toBeGreaterThan(0);
    expect(tables[0].name).toBe('Table 1');
    expect(tables[0].capacity).toBe(2);

    const waitlist = await service.getWaitlist();
    expect(waitlist.length).toBe(2);
    expect(waitlist[0].guest_name).toBe('John Doe');
    expect(waitlist[1].guest_name).toBe('Jane Smith');
  });

  it('should allow joining the waitlist and emit a QUEUE_UPDATE event', async () => {
    const listener = vi.fn();
    service.subscribe(listener);

    const newGuest = await service.joinWaitlist({
      guest_name: 'Alice Cooper',
      party_size: 3,
      phone_number: '555-1122',
    });

    expect(newGuest.id).toBeDefined();
    expect(newGuest.guest_name).toBe('Alice Cooper');
    expect(newGuest.party_size).toBe(3);
    expect(newGuest.status).toBe('WAITING');

    const waitlist = await service.getWaitlist();
    expect(waitlist.length).toBe(3);
    expect(waitlist[2].guest_name).toBe('Alice Cooper');

    expect(listener).toHaveBeenCalledWith('QUEUE_UPDATE');
  });

  it('should reject joining waitlist if arguments are invalid', async () => {
    await expect(
      service.joinWaitlist({ guest_name: '', party_size: 2, phone_number: '555' })
    ).rejects.toThrow('Guest name is required.');

    await expect(
      service.joinWaitlist({ guest_name: 'Alice', party_size: 0, phone_number: '555' })
    ).rejects.toThrow('Party size must be greater than zero.');
  });

  it('should notify a waiting guest, log SMS, and emit events', async () => {
    const listener = vi.fn();
    service.subscribe(listener);

    const waitlist = await service.getWaitlist();
    const targetPartyId = waitlist[0].id; // John Doe, status WAITING

    const updated = await service.notifyParty(targetPartyId);
    expect(updated.status).toBe('NOTIFIED');
    expect(updated.notified_at).not.toBeNull();

    const smsLogs = await service.getSmsLogs();
    expect(smsLogs.length).toBe(1);
    expect(smsLogs[0].phone_number).toBe('555-0199');
    expect(smsLogs[0].message).toContain('ready');

    expect(listener).toHaveBeenCalledWith('QUEUE_UPDATE');
    expect(listener).toHaveBeenCalledWith('SMS_UPDATE');
  });

  it('should not notify a guest who is not WAITING', async () => {
    const waitlist = await service.getWaitlist();
    const targetPartyId = waitlist[0].id;

    // Transition to NOTIFIED first
    await service.notifyParty(targetPartyId);

    // Transitioning again should throw
    await expect(service.notifyParty(targetPartyId)).rejects.toThrow(
      "Cannot notify a party with status 'NOTIFIED'."
    );
  });

  it('should seat a party at an eligible table and update states', async () => {
    const listener = vi.fn();
    service.subscribe(listener);

    const waitlist = await service.getWaitlist();
    const party = waitlist[0]; // John Doe, party_size = 2
    const tables = await service.getTables();
    const eligibleTable = tables[0]; // Table 1, capacity = 2, status AVAILABLE

    const { party: seatedParty, table: occupiedTable } = await service.seatParty(
      party.id,
      eligibleTable.id
    );

    expect(seatedParty.status).toBe('SEATED');
    expect(seatedParty.table_id).toBe(eligibleTable.id);
    expect(seatedParty.seated_at).not.toBeNull();

    expect(occupiedTable.status).toBe('OCCUPIED');
    expect(occupiedTable.current_party_id).toBe(party.id);

    expect(listener).toHaveBeenCalledWith('QUEUE_UPDATE');
    expect(listener).toHaveBeenCalledWith('TABLE_UPDATE');
  });

  it('should fail to seat a party if the table capacity is too small', async () => {
    const waitlist = await service.getWaitlist();
    const party = waitlist[1]; // Jane Smith, party_size = 4
    const tables = await service.getTables();
    const smallTable = tables[0]; // Table 1, capacity = 2

    expect(smallTable.capacity).toBeLessThan(party.party_size);

    await expect(service.seatParty(party.id, smallTable.id)).rejects.toThrow(
      /capacity.*is too small/
    );
  });

  it('should fail to seat a party if the table is already occupied', async () => {
    const waitlist = await service.getWaitlist();
    const firstParty = waitlist[0];
    const secondParty = waitlist[1];
    const tables = await service.getTables();
    const table = tables[4]; // Booth 5, capacity = 6

    // Seat first party
    await service.seatParty(firstParty.id, table.id);

    // Attempting to seat second party at same table should reject
    await expect(service.seatParty(secondParty.id, table.id)).rejects.toThrow(
      /currently not available/
    );
  });

  it('should cycle table state when cleared (OCCUPIED -> DIRTY -> AVAILABLE)', async () => {
    const waitlist = await service.getWaitlist();
    const party = waitlist[0];
    const tables = await service.getTables();
    const table = tables[0];

    // 1. Seat a party (Table becomes OCCUPIED)
    await service.seatParty(party.id, table.id);
    let currentTable = (await service.getTables())[0];
    expect(currentTable.status).toBe('OCCUPIED');

    // 2. Clear table (OCCUPIED -> DIRTY, party cleared)
    const cleared1 = await service.clearTable(table.id);
    expect(cleared1.status).toBe('DIRTY');
    expect(cleared1.current_party_id).toBeNull();

    // 3. Clear table again (DIRTY -> AVAILABLE)
    const cleared2 = await service.clearTable(table.id);
    expect(cleared2.status).toBe('AVAILABLE');
  });

  it('should clear table and restore availability when a seated guest is cancelled', async () => {
    const waitlist = await service.getWaitlist();
    const party = waitlist[0];
    const tables = await service.getTables();
    const table = tables[0];

    // Seat party
    await service.seatParty(party.id, table.id);

    // Cancel guest
    const cancelled = await service.cancelParty(party.id);
    expect(cancelled.status).toBe('CANCELLED');
    expect(cancelled.table_id).toBeNull();

    // Table should revert directly to AVAILABLE
    const updatedTables = await service.getTables();
    expect(updatedTables[0].status).toBe('AVAILABLE');
    expect(updatedTables[0].current_party_id).toBeNull();
  });
});
