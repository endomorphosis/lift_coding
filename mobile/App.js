import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';

import StatusScreen from './src/screens/StatusScreen';
import CommandScreen from './src/screens/CommandScreen';
import ConfirmationScreen from './src/screens/ConfirmationScreen';
import TTSScreen from './src/screens/TTSScreen';
import SettingsScreen from './src/screens/SettingsScreen';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor: '#007AFF',
          tabBarInactiveTintColor: 'gray',
        }}
      >
        <Tab.Screen
          name="Status"
          component={StatusScreen}
          options={{ title: 'Status' }}
        />
        <Tab.Screen
          name="Command"
          component={CommandScreen}
          options={{ title: 'Command' }}
        />
        <Tab.Screen
          name="Confirm"
          component={ConfirmationScreen}
          options={{ title: 'Confirm' }}
        />
        <Tab.Screen
          name="TTS"
          component={TTSScreen}
          options={{ title: 'TTS' }}
        />
        <Tab.Screen
          name="Settings"
          component={SettingsScreen}
          options={{ title: 'Settings' }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
