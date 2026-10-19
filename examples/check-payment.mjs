import assert from 'node:assert/strict';
import { allocatePayment } from './payment.mjs';
assert.deepEqual(allocatePayment(10000, 3000), { applied: 3000, balance: 7000, unapplied: 0 });
assert.deepEqual(allocatePayment(10000, 15000), { applied: 10000, balance: 0, unapplied: 5000 });
assert.throws(() => allocatePayment(100, -1), TypeError);
assert.throws(() => allocatePayment(100, 0.5), TypeError);
console.log('4 synthetic payment checks passed');
