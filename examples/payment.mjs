// Original synthetic fixture. Not a model of QuickBooks or any vendor product.
export function allocatePayment(balance, received) {
  if (![balance, received].every(value => Number.isSafeInteger(value) && value >= 0)) {
    throw new TypeError('Use nonnegative integer minor currency units');
  }
  const applied = Math.min(balance, received);
  return { applied, balance: balance - applied, unapplied: received - applied };
}
