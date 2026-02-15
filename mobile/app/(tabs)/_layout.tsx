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
          backgroundColor: c.headerBg,
          borderTopWidth: 0,
          height: 50,
          elevation: 0,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -1 },
          shadowOpacity: 0.1,
          shadowRadius: 2,
        },
        tabBarActiveTintColor: c.tabActive,
        tabBarInactiveTintColor: c.tabInactive,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 22 }}>💬</Text> }}
      />
      <Tabs.Screen
        name="windows"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 22 }}>🪟</Text> }}
      />
      <Tabs.Screen
        name="history"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 22 }}>📋</Text> }}
      />
      <Tabs.Screen
        name="settings"
        options={{ tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 22 }}>⚙️</Text> }}
      />
    </Tabs>
  );
}
