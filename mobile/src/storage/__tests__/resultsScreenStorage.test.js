jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  DEFAULT_RESULTS_SCREEN_STATE,
  RESULTS_SCREEN_STORAGE_KEY,
  getResultsScreenState,
  setResultsScreenState,
} from '../resultsScreenStorage';

describe('resultsScreenStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns defaults when nothing is stored', async () => {
    AsyncStorage.getItem.mockResolvedValue(null);

    await expect(getResultsScreenState()).resolves.toEqual(DEFAULT_RESULTS_SCREEN_STATE);
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(RESULTS_SCREEN_STORAGE_KEY);
  });

  it('merges stored state with defaults', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        selectedView: 'datasets',
        offset: 20,
        latestOnly: true,
        sort: 'created_at',
        direction: 'asc',
        lastAction: { actionId: 'pin_result', message: 'Pinned it.' },
        promptDraft: {
          actionId: 'rerun_dataset_search',
          taskId: 'task-123',
          promptKey: 'mcp_input',
          value: 'labor law datasets',
        },
      })
    );

    await expect(getResultsScreenState()).resolves.toEqual({
      selectedView: 'datasets',
      offset: 20,
      latestOnly: true,
      sort: 'created_at',
      direction: 'asc',
      lastAction: { actionId: 'pin_result', message: 'Pinned it.' },
      promptDraft: {
        actionId: 'rerun_dataset_search',
        taskId: 'task-123',
        promptKey: 'mcp_input',
        value: 'labor law datasets',
      },
    });
  });

  it('falls back to defaults for invalid stored offsets', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        selectedView: 'fetches',
        offset: -5,
        latestOnly: 'nope',
        sort: 'weird',
        direction: 'sideways',
      })
    );

    await expect(getResultsScreenState()).resolves.toEqual({
      ...DEFAULT_RESULTS_SCREEN_STATE,
      selectedView: 'fetches',
    });
  });

  it('persists the latest results screen state', async () => {
    AsyncStorage.setItem.mockResolvedValue(undefined);

    await setResultsScreenState({
      selectedView: 'ipfs',
      offset: 40,
      latestOnly: true,
      sort: 'created_at',
      direction: 'asc',
      lastAction: { actionId: 'share_cid', message: 'Shared bafy...' },
      promptDraft: {
        actionId: 'rerun_fetch_with_url',
        taskId: 'task-789',
        promptKey: 'mcp_seed_url',
        value: 'https://example.com',
      },
    });

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      RESULTS_SCREEN_STORAGE_KEY,
      JSON.stringify({
        selectedView: 'ipfs',
        offset: 40,
        latestOnly: true,
        sort: 'created_at',
        direction: 'asc',
        lastAction: { actionId: 'share_cid', message: 'Shared bafy...' },
        promptDraft: {
          actionId: 'rerun_fetch_with_url',
          taskId: 'task-789',
          promptKey: 'mcp_seed_url',
          value: 'https://example.com',
        },
      })
    );
  });
});
