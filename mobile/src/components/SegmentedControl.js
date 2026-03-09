import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function SegmentedControl({
  options,
  selectedValue,
  onChange,
  disabled = false,
}) {
  if (!Array.isArray(options) || options.length === 0) {
    return null;
  }

  return (
    <View style={styles.row}>
      {options.map((option) => {
        const selected = option.value === selectedValue;
        return (
          <TouchableOpacity
            key={option.value}
            style={[
              styles.chip,
              selected && styles.chipSelected,
              disabled && styles.chipDisabled,
            ]}
            onPress={() => onChange?.(option.value)}
            disabled={disabled}
          >
            <Text
              style={[
                styles.chipText,
                selected && styles.chipTextSelected,
              ]}
            >
              {option.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  chip: {
    backgroundColor: '#e5e7eb',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  chipSelected: {
    backgroundColor: '#111827',
  },
  chipDisabled: {
    opacity: 0.6,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  chipTextSelected: {
    color: '#fff',
  },
});
