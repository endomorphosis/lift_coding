import AsyncStorage from '@react-native-async-storage/async-storage';

export const RESULTS_SCREEN_STORAGE_KEY = '@handsfree_results_screen_state';

export const DEFAULT_RESULTS_SCREEN_STATE = {
  selectedView: 'overview',
  offset: 0,
  latestOnly: false,
  sort: 'updated_at',
  direction: 'desc',
  lastAction: null,
  promptDraft: null,
};

export async function getResultsScreenState() {
  try {
    const raw = await AsyncStorage.getItem(RESULTS_SCREEN_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_RESULTS_SCREEN_STATE };
    }

    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_RESULTS_SCREEN_STATE,
      ...(parsed && typeof parsed === 'object' ? parsed : {}),
      offset:
        typeof parsed?.offset === 'number' && parsed.offset >= 0
          ? parsed.offset
          : DEFAULT_RESULTS_SCREEN_STATE.offset,
      latestOnly:
        typeof parsed?.latestOnly === 'boolean'
          ? parsed.latestOnly
          : DEFAULT_RESULTS_SCREEN_STATE.latestOnly,
      sort:
        parsed?.sort === 'created_at' || parsed?.sort === 'updated_at'
          ? parsed.sort
          : DEFAULT_RESULTS_SCREEN_STATE.sort,
      direction:
        parsed?.direction === 'asc' || parsed?.direction === 'desc'
          ? parsed.direction
          : DEFAULT_RESULTS_SCREEN_STATE.direction,
    };
  } catch (error) {
    console.error('Failed to load results screen state from storage:', error);
    return { ...DEFAULT_RESULTS_SCREEN_STATE };
  }
}

export async function setResultsScreenState(state) {
  try {
    await AsyncStorage.setItem(
      RESULTS_SCREEN_STORAGE_KEY,
      JSON.stringify({
        ...DEFAULT_RESULTS_SCREEN_STATE,
        ...(state || {}),
      })
    );
  } catch (error) {
    console.error('Failed to save results screen state to storage:', error);
    throw error;
  }
}
