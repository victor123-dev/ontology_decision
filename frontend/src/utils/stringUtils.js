/**
 * Helper function to convert snake_case or kebab-case to camelCase
 * @param {string} str - The input string to convert
 * @returns {string} - The converted camelCase string
 */
export const toCamelCase = (str) => {
  if (!str) return '';
  // Replace hyphens and spaces with underscores, then split by underscore
  const parts = str.replace(/[-\s]/g, '_').split('_');
  return parts[0] + parts.slice(1).map(part => part.charAt(0).toUpperCase() + part.slice(1)).join('');
};

/**
 * Helper function to convert snake_case or kebab-case to PascalCase (UpperCamelCase)
 * @param {string} str - The input string to convert
 * @returns {string} - The converted PascalCase string
 */
export const toPascalCase = (str) => {
  if (!str) return '';
  // Replace hyphens and spaces with underscores, then split by underscore
  const parts = str.replace(/[-\s]/g, '_').split('_');
  return parts.map(part => part.charAt(0).toUpperCase() + part.slice(1)).join('');
};