import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';

export default function GlassesDiagnosticsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Glasses Audio Diagnostics</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Status</Text>
        <Text style={styles.text}>
          This screen is a scaffold for validating Bluetooth audio routing with Meta AI Glasses.
        </Text>
        <Text style={styles.text}>
          Next steps are implemented natively (see mobile/glasses/ios and mobile/glasses/android).
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>What to validate</Text>
        <Text style={styles.text}>- Bluetooth headset route is active</Text>
        <Text style={styles.text}>- Record a short clip from glasses mic</Text>
        <Text style={styles.text}>- Play it back through glasses speakers</Text>
        <Text style={styles.text}>- Export WAV for inspection</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Docs</Text>
        <Text style={styles.mono}>docs/meta-ai-glasses-audio-routing.md</Text>
        <Text style={styles.mono}>mobile/glasses/README.md</Text>
        <Text style={styles.mono}>mobile/glasses/TODO.md</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Note</Text>
        <Text style={styles.text}>
          Expo-managed apps can’t reliably control Bluetooth input/output routes without native
          code. This scaffold keeps the UI lightweight and tracks native implementation work.
        </Text>
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
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 6,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  text: {
    fontSize: 14,
    color: '#333',
    marginBottom: 6,
  },
  mono: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#555',
    marginBottom: 4,
  },
});
