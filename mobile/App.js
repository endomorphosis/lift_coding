import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { setupNotificationListeners } from './src/push';
import * as Linking from 'expo-linking';
import AsyncStorage from '@react-native-async-storage/async-storage';

import StatusScreen from './src/screens/StatusScreen';
import CommandScreen from './src/screens/CommandScreen';
import ConfirmationScreen from './src/screens/ConfirmationScreen';
import TTSScreen from './src/screens/TTSScreen';
import GlassesDiagnosticsScreen from './src/screens/GlassesDiagnosticsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { STORAGE_KEYS } from './src/api/config';

const Tab = createBottomTabNavigator();

// Deep linking configuration
const linking = {
  prefixes: ['handsfree://'],
  config: {
    screens: {
      Settings: 'oauth/callback',
    },
  },
};

export default function App() {
  useEffect(() => {
    // Set up notification listeners when app starts
    console.log('Setting up notification listeners');
    const cleanup = setupNotificationListeners((notification) => {
      console.log('Notification received in App:', notification);
    });

    // Clean up listeners when app unmounts
    return cleanup;
  }, []);

    // Handle initial URL if app was opened from a deep link
    const handleInitialURL = async () => {
      const initialUrl = await Linking.getInitialURL();
      if (initialUrl) {
        await handleDeepLink(initialUrl);
      }
    };

    // Handle URL events while app is running
    const subscription = Linking.addEventListener('url', (event) => {
      handleDeepLink(event.url);
    });

    handleInitialURL();

    return () => {
      subscription.remove();
    };
  }, []);

  const handleDeepLink = async (url) => {
    try {
      const { path, queryParams } = Linking.parse(url);
      
      // Check if this is an OAuth callback
      if (path === 'oauth/callback' && queryParams) {
        const { code, state } = queryParams;
        
        // Store the OAuth params temporarily so SettingsScreen can process them
        if (code && state) {
          await AsyncStorage.setItem(
            STORAGE_KEYS.GITHUB_OAUTH_PENDING,
            JSON.stringify({ code, state })
          );
        }
      }
    } catch (error) {
      console.error('Error handling deep link:', error);
    }
  };

  return (
    <NavigationContainer linking={linking}>
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
          name="Glasses"
          component={GlassesDiagnosticsScreen}
          options={{ title: 'Glasses' }}
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
