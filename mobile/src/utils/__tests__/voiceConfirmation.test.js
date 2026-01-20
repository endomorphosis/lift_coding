/**
 * Tests for voice confirmation utility
 * 
 * Tests the transcript → decision mapping logic
 * per PR-076 acceptance criteria.
 */

import { inferConfirmationDecision } from '../voiceConfirmation';

describe('inferConfirmationDecision', () => {
  describe('confirm keywords', () => {
    it('should return "confirm" for "yes"', () => {
      expect(inferConfirmationDecision('yes')).toBe('confirm');
    });

    it('should return "confirm" for "confirm"', () => {
      expect(inferConfirmationDecision('confirm')).toBe('confirm');
    });

    it('should return "confirm" for "do it"', () => {
      expect(inferConfirmationDecision('do it')).toBe('confirm');
    });

    it('should return "confirm" for "proceed"', () => {
      expect(inferConfirmationDecision('proceed')).toBe('confirm');
    });

    it('should return "confirm" for "ok"', () => {
      expect(inferConfirmationDecision('ok')).toBe('confirm');
    });

    it('should return "confirm" for "okay"', () => {
      expect(inferConfirmationDecision('okay')).toBe('confirm');
    });

    it('should return "confirm" for "approve"', () => {
      expect(inferConfirmationDecision('approve')).toBe('confirm');
    });

    it('should be case-insensitive for confirm', () => {
      expect(inferConfirmationDecision('YES')).toBe('confirm');
      expect(inferConfirmationDecision('Confirm')).toBe('confirm');
      expect(inferConfirmationDecision('OK')).toBe('confirm');
    });

    it('should handle confirm keywords with extra words', () => {
      expect(inferConfirmationDecision('yes please')).toBe('confirm');
      expect(inferConfirmationDecision('ok go ahead')).toBe('confirm');
      expect(inferConfirmationDecision('I want to confirm')).toBe('confirm');
    });
  });

  describe('cancel keywords', () => {
    it('should return "cancel" for "no"', () => {
      expect(inferConfirmationDecision('no')).toBe('cancel');
    });

    it('should return "cancel" for "cancel"', () => {
      expect(inferConfirmationDecision('cancel')).toBe('cancel');
    });

    it('should return "cancel" for "stop"', () => {
      expect(inferConfirmationDecision('stop')).toBe('cancel');
    });

    it('should return "cancel" for "never mind"', () => {
      expect(inferConfirmationDecision('never mind')).toBe('cancel');
    });

    it('should return "cancel" for "nevermind"', () => {
      expect(inferConfirmationDecision('nevermind')).toBe('cancel');
    });

    it('should return "cancel" for "abort"', () => {
      expect(inferConfirmationDecision('abort')).toBe('cancel');
    });

    it('should return "cancel" for "dont"', () => {
      expect(inferConfirmationDecision('dont')).toBe('cancel');
    });

    it('should return "cancel" for "don\'t"', () => {
      expect(inferConfirmationDecision("don't")).toBe('cancel');
    });

    it('should be case-insensitive for cancel', () => {
      expect(inferConfirmationDecision('NO')).toBe('cancel');
      expect(inferConfirmationDecision('Cancel')).toBe('cancel');
      expect(inferConfirmationDecision('STOP')).toBe('cancel');
    });

    it('should handle cancel keywords with extra words', () => {
      expect(inferConfirmationDecision('no thanks')).toBe('cancel');
      expect(inferConfirmationDecision('please stop')).toBe('cancel');
      expect(inferConfirmationDecision('I want to cancel')).toBe('cancel');
    });
  });

  describe('priority and ambiguity', () => {
    it('should prioritize cancel when both keywords present', () => {
      // Safety first: if user says "no" in any form, treat as cancel
      expect(inferConfirmationDecision('yes no')).toBe('cancel');
      expect(inferConfirmationDecision('confirm but cancel')).toBe('cancel');
      expect(inferConfirmationDecision('no wait yes')).toBe('cancel');
    });

    it('should return null for ambiguous/unclear input', () => {
      expect(inferConfirmationDecision('maybe')).toBe(null);
      expect(inferConfirmationDecision('I don\'t know')).toBe('cancel'); // has "don't"
      expect(inferConfirmationDecision('hmm')).toBe(null);
      expect(inferConfirmationDecision('uh')).toBe(null);
      expect(inferConfirmationDecision('what')).toBe(null);
      expect(inferConfirmationDecision('I know')).toBe(null); // "no" is substring, not word
    });

    it('should return null for empty or null input', () => {
      expect(inferConfirmationDecision('')).toBe(null);
      expect(inferConfirmationDecision('   ')).toBe(null);
      expect(inferConfirmationDecision(null)).toBe(null);
      expect(inferConfirmationDecision(undefined)).toBe(null);
    });

    it('should return null for unrelated phrases', () => {
      expect(inferConfirmationDecision('hello there')).toBe(null);
      expect(inferConfirmationDecision('what time is it')).toBe(null);
      expect(inferConfirmationDecision('the weather is nice')).toBe(null);
    });
  });

  describe('edge cases', () => {
    it('should handle whitespace', () => {
      expect(inferConfirmationDecision('  yes  ')).toBe('confirm');
      expect(inferConfirmationDecision('  no  ')).toBe('cancel');
      expect(inferConfirmationDecision('\nyes\n')).toBe('confirm');
    });

    it('should handle punctuation', () => {
      expect(inferConfirmationDecision('yes!')).toBe('confirm');
      expect(inferConfirmationDecision('no.')).toBe('cancel');
      expect(inferConfirmationDecision('confirm,')).toBe('confirm');
    });

    it('should handle partial word matches correctly', () => {
      // "ok" should match in "okay" and "ok"
      expect(inferConfirmationDecision('okay')).toBe('confirm');
      expect(inferConfirmationDecision('ok')).toBe('confirm');
      
      // "no" in "know" should NOT match (word boundary)
      expect(inferConfirmationDecision('I know')).toBe(null);
      
      // "ok" in "bokay" should NOT match (word boundary)
      expect(inferConfirmationDecision('bokay')).toBe(null);
      
      // But actual word "no" should match
      expect(inferConfirmationDecision('no way')).toBe('cancel');
      expect(inferConfirmationDecision('I said no')).toBe('cancel');
    });
  });

  describe('realistic transcription scenarios', () => {
    it('should handle confident affirmations', () => {
      expect(inferConfirmationDecision('Yes, do it')).toBe('confirm');
      expect(inferConfirmationDecision('Okay, proceed')).toBe('confirm');
      expect(inferConfirmationDecision('Confirm that action')).toBe('confirm');
    });

    it('should handle confident denials', () => {
      expect(inferConfirmationDecision('No, cancel that')).toBe('cancel');
      expect(inferConfirmationDecision('Stop, never mind')).toBe('cancel');
      expect(inferConfirmationDecision('Don\'t do that')).toBe('cancel');
    });

    it('should handle noisy transcriptions', () => {
      // When unclear, return null to prompt user to try again
      expect(inferConfirmationDecision('uh yes maybe')).toBe('confirm'); // has "yes"
      expect(inferConfirmationDecision('well no actually')).toBe('cancel'); // has "no"
      expect(inferConfirmationDecision('hmm let me think')).toBe(null);
    });
  });
});
