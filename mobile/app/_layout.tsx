import { useEffect, useState } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useChatStore } from '../stores/chatStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAutoMonitor } from '../hooks/useAutoMonitor';
import { useScheduler } from '../hooks/useScheduler';

export default function RootLayout() {
  const { host, token, theme } = useChatStore();
  const router = useRouter();
  const segments = useSegments();
  const [ready, setReady] = useState(false);
  useWebSocket();
  useAutoMonitor();
  useScheduler();

  useEffect(() => {
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const inLogin = segments[0] === 'login';
    if (!host || !token) {
      if (!inLogin) router.replace('/login');
    } else {
      if (inLogin) router.replace('/(tabs)');
    }
  }, [host, token, segments, ready]);

  return (
    <SafeAreaProvider>
      <StatusBar style={theme === 'dark' ? 'light' : 'dark'} />
      <Slot />
    </SafeAreaProvider>
  );
}
