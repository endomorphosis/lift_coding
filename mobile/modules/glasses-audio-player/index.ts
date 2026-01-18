import { NativeModulesProxy, EventEmitter, Subscription } from 'expo-modules-core';

// Import the native module. On web, it will be resolved to GlassesAudioPlayer.web.ts
// and on native platforms to GlassesAudioPlayer.(ios|android).ts
import GlassesAudioPlayerModule from './src/GlassesAudioPlayerModule';

export async function playAudio(fileUri: string): Promise<void> {
  return await GlassesAudioPlayerModule.playAudio(fileUri);
}

export async function stopAudio(): Promise<void> {
  return await GlassesAudioPlayerModule.stopAudio();
}

export async function isPlaying(): Promise<boolean> {
  return await GlassesAudioPlayerModule.isPlaying();
}
