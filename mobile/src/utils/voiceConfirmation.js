/**
 * Voice confirmation utility functions
 * 
 * Provides transcript interpretation for voice-based confirmations.
 * Used by mobile screens to parse yes/no responses from voice input.
 */

/**
 * Infer confirmation decision from transcript
 * 
 * @param {string} transcript - The transcribed text from voice input
 * @returns {'confirm' | 'cancel' | null} - Decision or null if unclear
 * 
 * Decision logic:
 * - Returns 'cancel' if any cancel keyword is detected (priority)
 * - Returns 'confirm' if any confirm keyword is detected
 * - Returns null if no keywords match (ambiguous/unclear)
 * 
 * Keywords are conservative to avoid false positives.
 * Uses word boundary matching to prevent partial word matches.
 */
export function inferConfirmationDecision(transcript) {
  if (!transcript) return null;

  const t = transcript.toLowerCase().trim();
  
  // Prefer explicit cancel if present (safety first)
  const cancelKeywords = ['cancel', 'stop', 'no', 'never mind', 'nevermind', 'abort', 'dont', "don't"];
  const confirmKeywords = ['confirm', 'yes', 'do it', 'proceed', 'ok', 'okay', 'approve'];

  // Use word boundary matching to avoid false positives (e.g., "know" containing "no")
  const hasKeyword = (keywords) => {
    return keywords.some((keyword) => {
      // For multi-word phrases, check as-is
      if (keyword.includes(' ')) {
        return t.includes(keyword);
      }
      // For single words, use word boundary regex
      // Escape special regex characters
      const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`\\b${escapedKeyword}\\b`, 'i');
      return regex.test(t);
    });
  };

  if (hasKeyword(cancelKeywords)) return 'cancel';
  if (hasKeyword(confirmKeywords)) return 'confirm';
  
  return null;
}
