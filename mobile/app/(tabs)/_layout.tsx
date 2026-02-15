import { Tabs } from 'expo-router';
import { Text } from 'react-native';
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
        tabBarStyle: {
          backgroundColor: theme === 'dark' ? 'rgba(23,33,43,0.92)' : 'rgba(255,255,255,0.92)',
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
