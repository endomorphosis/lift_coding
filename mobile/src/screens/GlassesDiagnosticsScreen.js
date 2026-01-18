import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, Alert, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { uploadDevAudio, sendAudioCommand } from '../api/client';
import GlassesAudio from '../../modules/glasses-audio';

const DEV_MODE_KEY = '@glasses_dev_mode';

export default function GlassesDiagnosticsScreen() {
  const [devMode, setDevMode] = useState(false);
  const [audioRoute, setAudioRoute] = useState('Unknown');
  const [audioRouteDetails, setAudioRouteDetails] = useState(null);
  const [connectionState, setConnectionState] = useState('Checking...');
  const [lastError, setLastError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState(null);
  const [lastRecordingUri, setLastRecordingUri] = useState(null);
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [commandResponse, setCommandResponse] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [nativeModuleAvailable, setNativeModuleAvailable] = useState(false);

  // Load dev mode setting and start monitoring
  useEffect(() => {
    loadDevMode();
    checkNativeModule();
    checkAudioRoute();
    setNativePlayerAvailable(isGlassesPlayerAvailable());

    // Start monitoring audio route changes (Android only)
    let subscription;
    if (Platform.OS === 'android') {
      try {
        GlassesAudio.startMonitoring();
        subscription = GlassesAudio.addAudioRouteChangeListener((event) => {
          console.log('Audio route changed:', event.route);
          updateAudioRouteFromNative(event.route);
        });
      } catch (error) {
        console.error('Failed to start audio monitoring:', error);
      }
    }

    // Cleanup
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      if (nativeModuleAvailable && !devMode) {
        GlassesAudio.stopMonitoring();
      }
    };
  }, []);

  // Monitor audio route when mode changes
  useEffect(() => {
    checkAudioRoute();
  }, [devMode, useNativeModule]);

  // Set up native module listeners
  useEffect(() => {
    if (!nativeModuleAvailable || devMode) return;

    const routeSubscription = GlassesAudio.addRouteChangeListener((event) => {
      setAudioRoute(event.route);
    });

    const recordingSubscription = GlassesAudio.addRecordingCompleteListener((event) => {
      if (event.error) {
        setLastError(`Recording failed: ${event.error}`);
      } else if (event.fileUri) {
        setLastRecordingUri(event.fileUri);
        Alert.alert('Recording Complete', `Saved to: ${event.fileUri}`);
      }
    });

    const playbackSubscription = GlassesAudio.addPlaybackCompleteListener((event) => {
      setIsPlaying(false);
      if (event.error) {
        setLastError(`Playback failed: ${event.error}`);
      }
    });

    return () => {
      routeSubscription.remove();
      recordingSubscription.remove();
      playbackSubscription.remove();
    };
  }, [nativeModuleAvailable, devMode]);

  const checkNativeModule = () => {
    const available = GlassesAudio.isAvailable();
    setNativeModuleAvailable(available);
    console.log('GlassesAudio native module available:', available);
  };

  const loadDevMode = async () => {
    try {
      const saved = await AsyncStorage.getItem(DEV_MODE_KEY);
      if (saved !== null) {
        setDevMode(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Failed to load dev mode:', error);
    }
  };

  const checkNativeModuleAvailability = () => {
    const isAvailable = GlassesAudio.isAvailable();
    setUseNativeModule(isAvailable);
    
    if (isAvailable) {
      console.log('✓ Native Glasses Audio module is available');
    } else {
      console.log('⚠️ Native Glasses Audio module not available, using Expo Audio fallback');
    }
  };

  const toggleDevMode = async (value) => {
    try {
      setDevMode(value);
      await AsyncStorage.setItem(DEV_MODE_KEY, JSON.stringify(value));
      setLastError(null);
      checkAudioRoute();
    } catch (error) {
      setLastError('Failed to save dev mode setting');
      console.error('Failed to save dev mode:', error);
    }
  };

  const formatDeviceList = (devices) => {
    if (!devices || devices.length === 0) return 'None';
    return devices.map(d => d.productName || d.typeName).join(', ');
  };

  const updateAudioRouteFromNative = (route) => {
    if (!route) return;

    setAudioRouteDetails(route);
    
    // Format the route information for display
    const inputDevices = formatDeviceList(route.inputs);
    const outputDevices = formatDeviceList(route.outputs);
    
    setAudioRoute(`In: ${inputDevices} | Out: ${outputDevices}`);
    
    // Update connection state
    if (route.isBluetoothConnected) {
      const scoStatus = route.isScoOn ? 'SCO Active' : 'SCO Inactive';
      setConnectionState(`✓ Bluetooth Connected (${scoStatus})`);
    } else {
      setConnectionState('⚠ No Bluetooth Device');
    }
  };

  const checkAudioRoute = async () => {
    try {
      // In glasses mode with native module available, use native Bluetooth APIs
      if (!devMode && useNativeModule) {
        const isConnected = await GlassesAudio.isBluetoothConnected();
        const routeSummary = await GlassesAudio.getCurrentRoute();
        
        if (isConnected) {
          setConnectionState('✓ Bluetooth Connected');
          setAudioRoute(routeSummary);
          setLastError(null);
          
          // Start route monitoring if not already started
          if (!routeSubscription) {
            const sub = await GlassesAudio.startRouteMonitoring((event) => {
              setAudioRoute(event.summary);
            });
            setRouteSubscription(sub);
          }
        } else {
          setConnectionState('⚠ No Bluetooth Device');
          setAudioRoute('Built-in mic/speaker');
        }
        return;
      }
      
      // In DEV mode or fallback mode, use Expo Audio
      // Request permissions
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        setConnectionState('Permission denied');
        setAudioRoute('No permission');
        setLastError('Microphone permission required');
        return;
      }

      // Set audio mode
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      if (devMode) {
        setConnectionState('✓ DEV Mode Active');
        setAudioRoute('Phone mic → Phone speaker');
      } else if (nativeModuleAvailable) {
        // Use native module to get actual route
        try {
          const route = await GlassesAudio.startMonitoring();
          setAudioRoute(route);
          setConnectionState('✓ Native module active');
        } catch (error) {
          console.error('Native module error:', error);
          setConnectionState('⚠ Native module error');
          setAudioRoute(error.message);
        }
      } else {
        // Native module not available
        setConnectionState('⚠ Glasses mode (native build required)');
        setAudioRoute('Native module not compiled. Run `expo prebuild` and build with Xcode/Android Studio.');
      }
      setLastError(null);
    } catch (error) {
      setLastError(`Audio setup failed: ${error.message}`);
      setConnectionState('✗ Error');
      setAudioRoute('Unknown');
      console.error('Audio route check failed:', error);
    }
  };

  const startRecording = async () => {
    try {
      setLastError(null);
      
      if (!devMode && nativeModuleAvailable) {
        // Use native module for glasses recording
        setIsRecording(true);
        const fileUri = await GlassesAudio.startRecording(10);
        // Recording will complete automatically after duration
      } else {
        // Use Expo Audio for dev mode
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });

        const { recording: newRecording } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY
        );
        setRecording(newRecording);
        setIsRecording(true);
      }
    } catch (error) {
      setLastError(`Recording failed: ${error.message}`);
      setIsRecording(false);
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      
      if (!devMode && nativeModuleAvailable) {
        // Stop native recording
        const fileUri = await GlassesAudio.stopRecording();
        setLastRecordingUri(fileUri);
        Alert.alert('Recording Complete', `Saved to: ${fileUri}`);
      } else if (recording) {
        // Stop Expo Audio recording
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        setRecording(null);
        setLastRecordingUri(uri);
        
        Alert.alert(
          'Recording Complete',
          `Audio saved locally.\n\nIn ${devMode ? 'DEV' : 'Glasses'} mode.\n\nReady to play back or send to backend.`,
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
      console.error('Failed to stop recording:', error);
    }
  };

  const playRecording = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setLastError(null);
      
      if (!devMode && nativeModuleAvailable) {
        // Use native module for glasses playback
        setIsPlaying(true);
        await GlassesAudio.playAudio(lastRecordingUri);
        // Playback completion will be handled by event listener
      } else {
        // Use Expo Audio for dev mode
        if (sound) {
          await sound.unloadAsync();
          setSound(null);
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: false,
          playThroughEarpieceAndroid: false,
        });

        const { sound: newSound } = await Audio.Sound.createAsync(
          { uri: lastRecordingUri },
          { shouldPlay: true }
        );
        
        setSound(newSound);
        setIsPlaying(true);

        newSound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) {
            setIsPlaying(false);
          }
        });

        Alert.alert(
          'Playing Recording',
          `Playback through ${devMode ? 'phone speaker' : 'glasses (if connected, else phone speaker)'}`
        );
      }
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      console.error('Failed to play recording:', error);
      setIsPlaying(false);
    }
  };

  const stopPlayback = async () => {
    try {
      if (!devMode && nativeModuleAvailable) {
        await GlassesAudio.stopPlayback();
      } else if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      }
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);
      console.error('Failed to stop playback:', error);
    }
  };

  const processAudioThroughPipeline = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setIsProcessing(true);
      setLastError(null);
      setCommandResponse(null);

      // Read audio file and encode as base64
      const audioBase64 = await FileSystem.readAsStringAsync(lastRecordingUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Determine format based on whether we used native or Expo recording
      const format = (!devMode && nativeModuleAvailable) ? 'wav' : 'm4a';

      // Upload to /v1/dev/audio
      const { uri: fileUri, format: returnedFormat } = await uploadDevAudio(audioBase64, format);

      // Send to /v1/command
      const response = await sendAudioCommand(fileUri, returnedFormat, {
        profile: 'dev',
        client_context: {
          device: 'mobile',
          app_version: '1.0.0',
          mode: devMode ? 'dev' : 'glasses',
        },
      });

      setCommandResponse(response);

      // If we have TTS audio in response and glasses mode is active, play it
      if (response.audio_base64 && !devMode && nativeModuleAvailable) {
        // Save TTS audio to file
        const ttsDir = FileSystem.documentDirectory + 'tts/';
        await FileSystem.makeDirectoryAsync(ttsDir, { intermediates: true });
        const ttsFilePath = ttsDir + `tts_${Date.now()}.wav`;
        await FileSystem.writeAsStringAsync(ttsFilePath, response.audio_base64, {
          encoding: FileSystem.EncodingType.Base64,
        });
        
        // Play TTS through glasses
        await GlassesAudio.playAudio(ttsFilePath);
        
        Alert.alert(
          'Pipeline Complete',
          `Command processed!\n\n"${response.spoken_text}"\n\nTTS playing through glasses...`,
          [{ text: 'OK' }]
        );
      } else {
        Alert.alert(
          'Pipeline Complete',
          `Command processed successfully!\n\n${response.spoken_text || 'Response received (no text content)'}\n\n${!devMode && nativeModuleAvailable ? 'TTS playback would play through glasses here' : 'Note: TTS playback not yet implemented for dev mode'}`,
          [{ text: 'OK' }]
        );
      }

    } catch (error) {
      setLastError(`Pipeline failed: ${error.message}`);
      console.error('Failed to process audio through pipeline:', error);
      Alert.alert('Error', `Failed to process command: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };


  const playRecording = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setLastError(null);
      
      // Use native module in glasses mode if available
      if (!devMode && useNativeModule) {
        await GlassesAudio.playAudio(lastRecordingUri);
        setIsPlaying(true);
        
        Alert.alert(
          'Playing Recording',
          'Playback through Bluetooth glasses speakers (native)'
        );
        return;
      }
      
      // Fallback to Expo Audio
      // Unload any existing sound
      if (sound) {
        await sound.unloadAsync();
        setSound(null);
      }

      // Configure audio mode for playback
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: false,
        playThroughEarpieceAndroid: false,
      });

      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: lastRecordingUri },
        { shouldPlay: true }
      );
      
      setSound(newSound);
      setIsPlaying(true);

      // Set up playback status update
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.didJustFinish) {
          setIsPlaying(false);
        }
      });

      Alert.alert(
        'Playing Recording',
        `Playback through ${devMode ? 'phone speaker' : 'glasses (if connected, else phone speaker)'}`
      );
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      console.error('Failed to play recording:', error);
      setIsPlaying(false);
    }
  };

  const stopPlayback = async () => {
    try {
      // Use native module in glasses mode if available
      if (!devMode && useNativeModule) {
        await GlassesAudio.stopPlayback();
        setIsPlaying(false);
        return;
      }
      
      // Fallback to Expo Audio
      if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      }
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);
      console.error('Failed to stop playback:', error);
    }
  };

  const playThroughNativeGlassesPlayer = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    if (!nativePlayerAvailable) {
      Alert.alert(
        'Native Player Unavailable',
        'The native glasses audio player is only available in iOS development builds. You are currently running in Expo Go or on Android.\n\nTo use this feature, create an iOS development build with:\n\nexpo prebuild\nexpo run:ios --device'
      );
      return;
    }

    try {
      setLastError(null);
      setIsPlayingNative(true);
      
      await playAudioThroughGlasses(lastRecordingUri);
      
      Alert.alert(
        'Playing Through Glasses',
        'Audio is now playing through your Meta AI Glasses speakers via Bluetooth.'
      );
    } catch (error) {
      setLastError(`Native playback failed: ${error.message}`);
      console.error('Failed to play through native player:', error);
      setIsPlayingNative(false);
      
      Alert.alert(
        'Playback Error',
        `Failed to play through glasses: ${error.message}\n\nMake sure:\n• Your Meta AI Glasses are paired via Bluetooth\n• Bluetooth is enabled\n• You're running on a physical iOS device`
      );
    }
  };

  const stopNativePlayback = async () => {
    try {
      await stopGlassesAudio();
      setIsPlayingNative(false);
    } catch (error) {
      setLastError(`Stop native playback failed: ${error.message}`);
      console.error('Failed to stop native playback:', error);
    }
  };

  const testAudioPipeline = () => {
    Alert.alert(
      'Audio Pipeline Flow',
      devMode
        ? '📱 DEV MODE\n\nRecord from: Phone mic\nPlayback through: Phone speaker\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n5. (TTS playback TBD)\n\n✓ Steps 1-4 implemented'
        : nativeModuleAvailable
        ? '👓 GLASSES MODE (Native)\n\nRecord from: Glasses mic (Bluetooth)\nPlayback through: Glasses speakers\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n5. Play TTS through glasses\n\n✓ Native module compiled\n✓ Full pipeline ready'
        : '👓 GLASSES MODE (Build Required)\n\nRecord from: Glasses mic (Bluetooth)\nPlayback through: Glasses speakers\n\n⚠️ Native module not available\n\nTo enable:\n1. Run `expo prebuild`\n2. Open ios/ or android/ in IDE\n3. Build and run native app',
      [{ text: 'OK' }]
    );
  };

  const getStatusIcon = () => {
    if (connectionState.includes('✓')) return '🟢';
    if (connectionState.includes('✗')) return '🔴';
    if (connectionState.includes('⚠')) return '🟡';
    return '⚪';
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Glasses Audio Diagnostics</Text>

      {/* Module Status */}
      {!nativeModuleAvailable && (
        <View style={[styles.card, styles.warningCard]}>
          <Text style={styles.cardTitle}>⚠️ Native Module Not Available</Text>
          <Text style={styles.text}>
            The native GlassesAudio module is not compiled. To use glasses mode:
          </Text>
          <Text style={styles.mono}>1. Run: expo prebuild</Text>
          <Text style={styles.mono}>2. Build with Xcode (iOS) or Android Studio</Text>
          <Text style={styles.text}>
            For now, use DEV mode to test with phone mic/speaker.
          </Text>
        </View>
      )}

      {/* Mode Toggle */}
      <View style={styles.card}>
        <View style={styles.toggleContainer}>
          <View style={styles.toggleLabel}>
            <Text style={styles.cardTitle}>
              {devMode ? '📱 DEV Mode' : '👓 Glasses Mode'}
            </Text>
            <Text style={styles.subtext}>
              {devMode
                ? 'Phone mic/speaker for rapid iteration'
                : nativeModuleAvailable
                ? 'Glasses mic/speaker via native Bluetooth'
                : 'Requires native build (see warning above)'}
            </Text>
          </View>
          <Switch
            value={devMode}
            onValueChange={toggleDevMode}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={devMode ? '#007AFF' : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Connection State */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connection State</Text>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Status:</Text>
          <Text style={styles.statusValue}>
            {getStatusIcon()} {connectionState}
          </Text>
        </View>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Audio Route:</Text>
          <Text style={[styles.statusValue, styles.routeText]}>{audioRoute}</Text>
        </View>
        <TouchableOpacity 
          style={[styles.button, styles.buttonSecondary]} 
          onPress={checkAudioRoute}
        >
          <Text style={styles.buttonTextSecondary}>🔄 Refresh Status</Text>
        </TouchableOpacity>
      </View>

      {/* Detailed Audio Route (Android only) */}
      {Platform.OS === 'android' && !devMode && audioRouteDetails && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📡 Detailed Audio Routing</Text>
          
          {audioRouteDetails.inputs && audioRouteDetails.inputs.length > 0 && (
            <View style={styles.detailSection}>
              <Text style={styles.detailTitle}>Input Devices:</Text>
              {audioRouteDetails.inputs.map((device, index) => (
                <Text key={index} style={styles.detailText}>
                  • {device.productName || device.typeName}
                </Text>
              ))}
            </View>
          )}

          {audioRouteDetails.outputs && audioRouteDetails.outputs.length > 0 && (
            <View style={styles.detailSection}>
              <Text style={styles.detailTitle}>Output Devices:</Text>
              {audioRouteDetails.outputs.map((device, index) => (
                <Text key={index} style={styles.detailText}>
                  • {device.productName || device.typeName}
                </Text>
              ))}
            </View>
          )}

          <View style={styles.detailSection}>
            <Text style={styles.detailTitle}>Audio Settings:</Text>
            <Text style={styles.detailText}>
              Mode: {audioRouteDetails.audioModeName}
            </Text>
            <Text style={styles.detailText}>
              Bluetooth SCO: {audioRouteDetails.isScoOn ? '✓ Active' : '✗ Inactive'}
              {audioRouteDetails.isScoAvailable && ' (Available)'}
            </Text>
            <Text style={styles.detailText}>
              Bluetooth Device: {audioRouteDetails.isBluetoothConnected ? '✓ Connected' : '✗ Not Connected'}
            </Text>
          </View>
        </View>
      )}

      {/* Error Display */}
      {lastError && (
        <View style={[styles.card, styles.errorCard]}>
          <Text style={styles.cardTitle}>⚠️ Last Error</Text>
          <Text style={styles.errorText}>{lastError}</Text>
          <TouchableOpacity 
            style={[styles.button, styles.buttonSecondary]} 
            onPress={() => setLastError(null)}
          >
            <Text style={styles.buttonTextSecondary}>Clear Error</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Recording Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Recording</Text>
        <Text style={styles.text}>
          {devMode
            ? '📱 Recording from phone microphone'
            : nativeModuleAvailable
            ? '👓 Recording from glasses microphone'
            : '⚠️ Native build required for glasses recording'}
        </Text>
        <TouchableOpacity
          style={[styles.button, isRecording && styles.buttonRecording]}
          onPress={isRecording ? stopRecording : startRecording}
        >
          <Text style={styles.buttonText}>
            {isRecording ? '⏹ Stop Recording' : '🎤 Start Recording'}
          </Text>
        </TouchableOpacity>
        {lastRecordingUri && (
          <Text style={styles.successText}>✓ Recording saved locally</Text>
        )}
      </View>

      {/* Playback Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Playback (Local)</Text>
        <Text style={styles.text}>
          {devMode
            ? '📱 Playing through phone speaker'
            : nativeModuleAvailable
            ? '👓 Playing through glasses speakers'
            : '⚠️ Native build required for glasses playback'}
        </Text>
        <TouchableOpacity
          style={[
            styles.button,
            !lastRecordingUri && styles.buttonDisabled,
            isPlaying && styles.buttonRecording,
          ]}
          onPress={isPlaying ? stopPlayback : playRecording}
          disabled={!lastRecordingUri}
        >
          <Text style={styles.buttonText}>
            {isPlaying ? '⏹ Stop Playback' : '▶️ Play Last Recording'}
          </Text>
        </TouchableOpacity>
        {!lastRecordingUri && (
          <Text style={styles.hintText}>Record audio first to enable playback</Text>
        )}
      </View>

      {/* Native Glasses Player */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>👓 Native Glasses Player (iOS)</Text>
        <Text style={styles.text}>
          Play audio through Meta AI Glasses using native AVAudioEngine with Bluetooth routing.
        </Text>
        {nativePlayerAvailable ? (
          <>
            <Text style={styles.successText}>✓ Native player available</Text>
            <TouchableOpacity
              style={[
                styles.button,
                !lastRecordingUri && styles.buttonDisabled,
                isPlayingNative && styles.buttonRecording,
              ]}
              onPress={isPlayingNative ? stopNativePlayback : playThroughNativeGlassesPlayer}
              disabled={!lastRecordingUri}
            >
              <Text style={styles.buttonText}>
                {isPlayingNative ? '⏹ Stop Native Playback' : '🔊 Play Through Glasses'}
              </Text>
            </TouchableOpacity>
            {!lastRecordingUri && (
              <Text style={styles.hintText}>Record audio first to enable playback</Text>
            )}
            <Text style={styles.hintText}>
              Ensure Meta AI Glasses are paired via Bluetooth
            </Text>
          </>
        ) : (
          <>
            <Text style={styles.errorText}>
              ⚠️ Native player only available in iOS development builds
            </Text>
            <Text style={styles.hintText}>
              Current platform: {Platform.OS}
              {Platform.OS === 'ios' ? ' (running in Expo Go)' : ''}
            </Text>
            <Text style={styles.hintText}>
              Create a dev build with: expo prebuild && expo run:ios --device
            </Text>
          </>
        )}
      </View>

      {/* Backend Pipeline Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Backend Command Pipeline</Text>
        <Text style={styles.text}>
          Process recording through backend pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command → TTS
        </Text>
        <TouchableOpacity
          style={[
            styles.button,
            (!lastRecordingUri || isProcessing) && styles.buttonDisabled,
          ]}
          onPress={processAudioThroughPipeline}
          disabled={!lastRecordingUri || isProcessing}
        >
          <Text style={styles.buttonText}>
            {isProcessing ? '⏳ Processing...' : '🚀 Send to Backend & Get Response'}
          </Text>
        </TouchableOpacity>
        {!lastRecordingUri && (
          <Text style={styles.hintText}>Record audio first to enable</Text>
        )}
        {commandResponse && (
          <View style={styles.responseContainer}>
            <Text style={styles.responseTitle}>Backend Response:</Text>
            <Text style={styles.responseText}>{commandResponse.spoken_text}</Text>
            {commandResponse.ui_cards && commandResponse.ui_cards.length > 0 && (
              <Text style={styles.hintText}>
                {commandResponse.ui_cards.length} UI card(s) received
              </Text>
            )}
          </View>
        )}
      </View>

      {/* Pipeline Info */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Command Pipeline</Text>
        <Text style={styles.text}>
          Both modes use the same backend pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command → Response
        </Text>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={testAudioPipeline}>
          <Text style={styles.buttonTextSecondary}>ℹ️ View Pipeline Details</Text>
        </TouchableOpacity>
      </View>

      {/* Implementation Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Implementation Status</Text>
        <Text style={styles.text}>✓ DEV mode (phone mic/speaker) - Working</Text>
        <Text style={styles.text}>✓ Recording and playback - Working</Text>
        <Text style={styles.text}>✓ Backend pipeline integration - Working</Text>
        <Text style={styles.text}>✓ Error handling - Working</Text>
        <Text style={styles.text}>
          {nativeModuleAvailable ? '✓ Native module - Available' : '⚠ Native module - Requires build'}
        </Text>
        <Text style={styles.text}>
          {nativeModuleAvailable ? '✓ Glasses mode - Ready' : '⏳ Glasses mode - Pending native build'}
        </Text>
      </View>

      {/* Docs */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Documentation</Text>
        <Text style={styles.mono}>docs/meta-ai-glasses-audio-routing.md</Text>
        <Text style={styles.mono}>mobile/glasses/README.md</Text>
        <Text style={styles.mono}>mobile/glasses/TODO.md</Text>
        <Text style={styles.mono}>mobile/modules/glasses-audio/</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  warningCard: {
    backgroundColor: '#fff3cd',
    borderLeftWidth: 4,
    borderLeftColor: '#ff9800',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    color: '#000',
  },
  text: {
    fontSize: 14,
    color: '#333',
    marginBottom: 6,
    lineHeight: 20,
  },
  mono: {
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    color: '#555',
    marginBottom: 4,
    backgroundColor: '#f5f5f5',
    padding: 8,
    borderRadius: 4,
  },
  toggleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toggleLabel: {
    flex: 1,
    marginRight: 12,
  },
  subtext: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    lineHeight: 16,
  },
  statusRow: {
    flexDirection: 'row',
    marginBottom: 8,
    alignItems: 'flex-start',
  },
  statusLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    width: 100,
  },
  statusValue: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  routeText: {
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 11,
  },
  errorCard: {
    backgroundColor: '#fff3cd',
    borderLeftWidth: 4,
    borderLeftColor: '#ff9800',
  },
  errorText: {
    color: '#d32f2f',
    fontSize: 14,
    marginBottom: 8,
  },
  successText: {
    color: '#4caf50',
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  hintText: {
    color: '#999',
    fontSize: 12,
    marginTop: 8,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonSecondary: {
    backgroundColor: '#f0f0f0',
  },
  buttonRecording: {
    backgroundColor: '#d32f2f',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
    opacity: 0.6,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonTextSecondary: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  responseContainer: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#e8f5e9',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#4caf50',
  },
  responseTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2e7d32',
    marginBottom: 6,
  },
  responseText: {
    fontSize: 14,
    color: '#1b5e20',
    lineHeight: 20,
  },
  detailSection: {
    marginBottom: 12,
  },
  detailTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  detailText: {
    fontSize: 13,
    color: '#555',
    marginLeft: 8,
    marginBottom: 2,
    lineHeight: 18,
  },
});
