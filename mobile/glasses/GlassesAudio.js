/**
 * GlassesAudio - React Native bridge for Android glasses audio recording and playback
 * 
 * This module provides native Android functionality for:
 * - Recording audio from Bluetooth glasses microphone
 * - Playing audio through Bluetooth glasses speakers
 * - Managing Bluetooth SCO connections
 * - Writing/reading 16kHz mono WAV files
 */

import { NativeModules, Platform } from 'react-native';

const { GlassesAudioModule } = NativeModules;

/**
 * Check if the native module is available
 */
export const isAvailable = () => {
  return Platform.OS === 'android' && GlassesAudioModule != null;
};

/**
 * Get current audio route information
 * @returns {Promise<string>} Audio route description
 */
export const getAudioRoute = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.getAudioRoute();
};

/**
 * Start recording audio
 * @param {number} durationMs Recording duration in milliseconds (0 = unlimited)
 * @returns {Promise<{filePath: string, duration: number}>} Recording result
 */
export const startRecording = async (durationMs = 10000) => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.startRecording(durationMs);
};

/**
 * Stop recording
 * @returns {Promise<void>}
 */
export const stopRecording = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.stopRecording();
};

/**
 * Check if currently recording
 * @returns {Promise<boolean>}
 */
export const isRecording = async () => {
  if (!isAvailable()) {
    return false;
  }
  return await GlassesAudioModule.isRecording();
};

/**
 * Play audio from a file
 * @param {string} filePath Path to audio file
 * @returns {Promise<void>}
 */
export const playAudio = async (filePath) => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.playAudio(filePath);
};

/**
 * Play the last recorded audio
 * @returns {Promise<void>}
 */
export const playLastRecording = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.playLastRecording();
};

/**
 * Stop playback
 * @returns {Promise<void>}
 */
export const stopPlayback = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.stopPlayback();
};

/**
 * Pause playback
 * @returns {Promise<void>}
 */
export const pausePlayback = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.pausePlayback();
};

/**
 * Resume playback
 * @returns {Promise<void>}
 */
export const resumePlayback = async () => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.resumePlayback();
};

/**
 * Check if currently playing
 * @returns {Promise<boolean>}
 */
export const isPlaying = async () => {
  if (!isAvailable()) {
    return false;
  }
  return await GlassesAudioModule.isPlaying();
};

/**
 * Get last recording file path
 * @returns {Promise<string|null>}
 */
export const getLastRecordingPath = async () => {
  if (!isAvailable()) {
    return null;
  }
  return await GlassesAudioModule.getLastRecordingPath();
};

/**
 * List all recordings
 * @returns {Promise<Array<{path: string, name: string, size: number, timestamp: number}>>}
 */
export const listRecordings = async () => {
  if (!isAvailable()) {
    return [];
  }
  return await GlassesAudioModule.listRecordings();
};

/**
 * Delete a recording
 * @param {string} filePath Path to recording file
 * @returns {Promise<boolean>}
 */
export const deleteRecording = async (filePath) => {
  if (!isAvailable()) {
    throw new Error('GlassesAudioModule is only available on Android');
  }
  return await GlassesAudioModule.deleteRecording(filePath);
};

export default {
  isAvailable,
  getAudioRoute,
  startRecording,
  stopRecording,
  isRecording,
  playAudio,
  playLastRecording,
  stopPlayback,
  pausePlayback,
  resumePlayback,
  isPlaying,
  getLastRecordingPath,
  listRecordings,
  deleteRecording,
};
