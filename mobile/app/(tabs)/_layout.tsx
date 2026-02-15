import { Tabs } from 'expo-router';
import { Text, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
import { useChatStore } from '../../stores/chatStore';
import { Colors } from '../../constants/theme';

export default function TabLayout() {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarShowLabel: false,
        tabBarBackground: () => (
          <BlurView
            intensity={80}
            tint={theme === 'dark' ? 'dark' : 'light'}
            style={StyleSheet.absoluteFill}
          />
        ),
        tabBarStyle: {
          backgroundColor: theme === 'dark' ? 'rgba(23,33,43,0.65)' : 'rgba(255,255,255,0.65)',
          borderTopWidth: 0,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 56,
          paddingBottom: 4,
          elevation: 0,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -4 },
          shadowOpacity: 0.15,
          shadowRadius: 8,
        },
        tabBarActiveTintColor: c.tabActive,
        tabBarInactiveTintColor: c.tabInactive,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 24 }}>💬</Text> }}
      />
      <Tabs.Screen
        name="windows"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 24 }}>🪟</Text> }}
      />
      <Tabs.Screen
        name="history"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 24 }}>📋</Text> }}
      />
      <Tabs.Screen
        name="settings"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 24 }}>⚙️</Text> }}
      />
    </Tabs>
  );
}
