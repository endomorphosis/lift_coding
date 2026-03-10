import { useCallback, useEffect, useRef, useState } from 'react';

import { getMetaWearablesDat } from '../native/metaWearablesDat';
import { mergeMetaWearablesDatState } from '../utils/metaWearablesDatState';

function getModuleAvailability(module) {
  if (!module) {
    return false;
  }
  if (typeof module.isBridgeAvailable === 'function') {
    return Boolean(module.isBridgeAvailable());
  }
  if (typeof module.isAvailable === 'function') {
    return Boolean(module.isAvailable());
  }
  return false;
}

export function useMetaWearablesDat(options = {}) {
  const { onError, onStateChanged } = options;
  const [isAvailable, setIsAvailable] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [sessionState, setSessionState] = useState('unknown');
  const [candidates, setCandidates] = useState([]);
  const moduleRef = useRef(null);
  const onErrorRef = useRef(onError);
  const onStateChangedRef = useRef(onStateChanged);

  useEffect(() => {
    onErrorRef.current = onError;
    onStateChangedRef.current = onStateChanged;
  }, [onError, onStateChanged]);

  const resolveModule = useCallback(async () => {
    if (moduleRef.current) {
      return moduleRef.current;
    }
    const module = await getMetaWearablesDat();
    moduleRef.current = module;
    setIsAvailable(getModuleAvailability(module));
    return module;
  }, []);

  const refreshDiagnostics = useCallback(async (scanTimeoutMs = 2000) => {
    try {
      const module = await resolveModule();
      setIsAvailable(getModuleAvailability(module));
      const diagnosticsResponse = await module.getDiagnostics();
      const candidateResponse = typeof module.scanKnownAndNearbyDevices === 'function'
        ? await module.scanKnownAndNearbyDevices(scanTimeoutMs)
        : [];
      setDiagnostics(diagnosticsResponse);
      setSessionState(diagnosticsResponse?.sessionState || 'unknown');
      setCandidates(Array.isArray(candidateResponse) ? candidateResponse : []);
      return {
        diagnostics: diagnosticsResponse,
        candidates: Array.isArray(candidateResponse) ? candidateResponse : [],
      };
    } catch (error) {
      onErrorRef.current?.(`Wearables bridge diagnostics failed: ${error.message}`);
      throw error;
    }
  }, [resolveModule]);

  useEffect(() => {
    refreshDiagnostics().catch(() => {});
  }, [refreshDiagnostics]);

  useEffect(() => {
    let cancelled = false;
    let subscription = null;

    resolveModule()
      .then((module) => {
        if (cancelled || !module?.addStateListener) {
          return;
        }
        subscription = module.addStateListener((event) => {
          setSessionState(event?.state || 'unknown');
          setDiagnostics((current) => mergeMetaWearablesDatState(current, event));
          onStateChangedRef.current?.(event);
          refreshDiagnostics().catch(() => {});
        });
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      try {
        subscription?.remove?.();
      } catch {
        // ignore cleanup errors from native event bridges
      }
    };
  }, [refreshDiagnostics, resolveModule]);

  const runAction = useCallback(async (actionName, errorPrefix, ...args) => {
    try {
      const module = await resolveModule();
      if (typeof module?.[actionName] !== 'function') {
        throw new Error(`Wearables bridge action ${actionName} is unavailable`);
      }
      const result = await module[actionName](...args);
      if (result?.state) {
        setSessionState(result.state);
      }
      await refreshDiagnostics();
      return result;
    } catch (error) {
      onErrorRef.current?.(`${errorPrefix}: ${error.message}`);
      throw error;
    }
  }, [refreshDiagnostics, resolveModule]);

  const startBridgeSession = useCallback(async () => {
    return await runAction('startBridgeSession', 'Wearables bridge session start failed');
  }, [runAction]);

  const stopBridgeSession = useCallback(async () => {
    return await runAction('stopBridgeSession', 'Wearables bridge session stop failed');
  }, [runAction]);

  const selectDeviceTarget = useCallback(async (deviceId) => {
    return await runAction('selectDeviceTarget', 'Wearables bridge target select failed', deviceId);
  }, [runAction]);

  const clearDeviceTarget = useCallback(async () => {
    return await runAction('clearDeviceTarget', 'Wearables bridge target clear failed');
  }, [runAction]);

  const reconnectSelectedDeviceTarget = useCallback(async () => {
    return await runAction('reconnectSelectedDeviceTarget', 'Wearables bridge reconnect failed');
  }, [runAction]);

  const connectSelectedDeviceTarget = useCallback(async () => {
    return await runAction('connectSelectedDeviceTarget', 'Wearables bridge connect failed');
  }, [runAction]);

  const capturePhoto = useCallback(async () => {
    return await runAction('capturePhoto', 'Wearables DAT photo capture failed');
  }, [runAction]);

  const startVideoStream = useCallback(async () => {
    return await runAction('startVideoStream', 'Wearables DAT video start failed');
  }, [runAction]);

  const stopVideoStream = useCallback(async () => {
    return await runAction('stopVideoStream', 'Wearables DAT video stop failed');
  }, [runAction]);

  return {
    isAvailable,
    diagnostics,
    sessionState,
    candidates,
    refreshDiagnostics,
    startBridgeSession,
    stopBridgeSession,
    selectDeviceTarget,
    clearDeviceTarget,
    reconnectSelectedDeviceTarget,
    connectSelectedDeviceTarget,
    capturePhoto,
    startVideoStream,
    stopVideoStream,
  };
}