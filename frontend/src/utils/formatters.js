// Number formatting utility functions

/**
 * Safely convert a value to a number
 * @param {any} value - Value to convert
 * @param {number} fallback - Fallback value if conversion fails
 * @returns {number} The converted number or fallback
 */
export const toNumber = (value, fallback = 0) => {
  if (value === null || value === undefined || value === '') return fallback;
  const num = Number(value);
  return isNaN(num) ? fallback : num;
};

/**
 * Format a number as currency
 * @param {number|string} value - The number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number with specified decimal places
 */
export const formatCurrency = (value, decimals = 2) => {
  // Convert to number, handle NaN and return string with fixed decimals
  const num = Number(value);
  return isNaN(num) ? '0.00' : num.toFixed(decimals);
};

/**
 * Format a date string
 * @param {string} dateString - ISO date string 
 * @returns {string} Formatted date
 */
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    console.error('Date formatting error:', e);
    return dateString;
  }
};