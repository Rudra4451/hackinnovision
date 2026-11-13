import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Robust, leak-free state machine hook for rover trajectory simulation (§4.2).
 */
export function useSimulation(path = [], options = {}) {
  const { initialSpeed = 1.0, onStep = null } = options;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [status, setStatus] = useState('READY'); // 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED'
  const [speed, setSpeed] = useState(initialSpeed); // 0.5, 1, 2, 4

  const intervalRef = useRef(null);
  const isMountedRef = useRef(true);

  const pathLength = Array.isArray(path) ? path.length : 0;
  const maxIndex = Math.max(0, pathLength - 1);

  // Clear running timers
  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Safe status update
  const updateStatus = useCallback((newStatus) => {
    if (isMountedRef.current) {
      setStatus(newStatus);
    }
  }, []);

  // Reset to initial origin
  const reset = useCallback(() => {
    clearTimer();
    if (isMountedRef.current) {
      setCurrentIndex(0);
      setStatus(pathLength > 0 ? 'READY' : 'FAILED');
      if (onStep) onStep(0);
    }
  }, [clearTimer, pathLength, onStep]);

  // Pause traversal
  const pause = useCallback(() => {
    clearTimer();
    updateStatus('PAUSED');
  }, [clearTimer, updateStatus]);

  // Start or resume execution
  const start = useCallback(() => {
    if (pathLength <= 0) {
      updateStatus('FAILED');
      return;
    }

    clearTimer();
    updateStatus('RUNNING');

    // Base interval: 250ms at 1x speed
    const tickIntervalMs = Math.max(50, Math.round(250 / speed));

    intervalRef.current = setInterval(() => {
      if (!isMountedRef.current) return;

      setCurrentIndex((prev) => {
        if (prev >= maxIndex) {
          clearTimer();
          updateStatus('COMPLETED');
          return maxIndex;
        }
        const next = prev + 1;
        if (onStep) onStep(next);
        if (next >= maxIndex) {
          clearTimer();
          updateStatus('COMPLETED');
        }
        return next;
      });
    }, tickIntervalMs);
  }, [pathLength, clearTimer, updateStatus, speed, maxIndex, onStep]);

  // Step single frame forward
  const stepForward = useCallback(() => {
    clearTimer();
    if (status === 'RUNNING') updateStatus('PAUSED');
    setCurrentIndex((prev) => {
      const next = Math.min(maxIndex, prev + 1);
      if (onStep) onStep(next);
      return next;
    });
  }, [clearTimer, status, updateStatus, maxIndex, onStep]);

  // Step single frame backward
  const stepBackward = useCallback(() => {
    clearTimer();
    if (status === 'RUNNING') updateStatus('PAUSED');
    setCurrentIndex((prev) => {
      const next = Math.max(0, prev - 1);
      if (onStep) onStep(next);
      return next;
    });
  }, [clearTimer, status, updateStatus, onStep]);

  // Seek directly to index (scrubber)
  const seekTo = useCallback((index) => {
    clearTimer();
    if (status === 'RUNNING') updateStatus('PAUSED');
    const clamped = Math.max(0, Math.min(maxIndex, Number(index)));
    setCurrentIndex(clamped);
    if (onStep) onStep(clamped);
  }, [clearTimer, status, updateStatus, maxIndex, onStep]);

  // Speed multiplier update
  const changeSpeed = useCallback((newSpeed) => {
    setSpeed(newSpeed);
    if (status === 'RUNNING') {
      clearTimer();
      // Re-trigger start with new speed
      const tickIntervalMs = Math.max(50, Math.round(250 / newSpeed));
      intervalRef.current = setInterval(() => {
        if (!isMountedRef.current) return;
        setCurrentIndex((prev) => {
          if (prev >= maxIndex) {
            clearTimer();
            updateStatus('COMPLETED');
            return maxIndex;
          }
          const next = prev + 1;
          if (onStep) onStep(next);
          if (next >= maxIndex) {
            clearTimer();
            updateStatus('COMPLETED');
          }
          return next;
        });
      }, tickIntervalMs);
    }
  }, [status, clearTimer, maxIndex, onStep, updateStatus]);

  // Reset when path changes
  useEffect(() => {
    if (pathLength === 0) {
      clearTimer();
      setCurrentIndex(0);
      setStatus('READY');
    }
  }, [pathLength, clearTimer]);

  // Lifecycle cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimer();
    };
  }, [clearTimer]);

  const currentCoordinate = path[currentIndex] || null;
  const progressPct = maxIndex > 0 ? (currentIndex / maxIndex) * 100 : 0;

  return {
    currentIndex,
    currentCoordinate,
    status,
    speed,
    progressPct,
    maxIndex,
    start,
    pause,
    resume: start,
    stepForward,
    stepBackward,
    reset,
    seekTo,
    setSpeed: changeSpeed,
  };
}
