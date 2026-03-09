import React from 'react';
import {
  Alert,
  Button,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

export default function ActionPromptModal({
  visible,
  title,
  promptLabel,
  value,
  onChangeValue,
  onCancel,
  onRun,
}) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onCancel}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalCard}>
          <Text style={styles.modalTitle}>{title || 'Action'}</Text>
          <Text style={styles.modalText}>{promptLabel || 'Enter a value'}</Text>
          <TextInput
            style={styles.modalInput}
            value={value}
            onChangeText={onChangeValue}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder={promptLabel || 'Value'}
          />
          <View style={styles.modalButtons}>
            <View style={styles.modalButton}>
              <Button title="Cancel" onPress={onCancel} color="#666" />
            </View>
            <View style={styles.modalButton}>
              <Button
                title="Run"
                onPress={() => {
                  if (!String(value || '').trim()) {
                    Alert.alert('Missing Value', 'Enter a value before running this action.');
                    return;
                  }
                  onRun?.();
                }}
              />
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    padding: 20,
  },
  modalCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  modalText: {
    fontSize: 14,
    color: '#555',
    marginBottom: 10,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    backgroundColor: '#fff',
  },
  modalButtons: {
    flexDirection: 'row',
    marginTop: 16,
  },
  modalButton: {
    flex: 1,
    marginRight: 8,
  },
});
