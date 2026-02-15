import { View, Text, TouchableOpacity, Switch, StyleSheet, ScrollView, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState, useCallback } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useApi } from '../../hooks/useApi';
import { Colors } from '../../constants/theme';

export default function SettingsScreen() {
  const { host, theme, setTheme, clearAuth } = useChatStore();
  const router = useRouter();
  const c = Colors[theme];
  const api = useApi();
  const [config, setConfig] = useState<any>({});

  useEffect(() => {
    api.getStatus().then((res) => {
      if (res.ok) setConfig(res.data);
    });
  }, []);

  const toggleConfig = useCallback(async (key: string, value: any) => {
    const res = await api.updateConfig({ [key]: value });
    if (res.ok) setConfig((prev: any) => ({ ...prev, [key]: value }));
    else Alert.alert('错误', res.error || '更新失败');
  }, []);

  const handleLogout = () => {
    clearAuth();
    router.replace('/login');
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: c.background }]}>
      <View style={[styles.headerBar, { backgroundColor: c.headerBg }]}>
        <Text style={[styles.header, { color: c.headerText }]}>设置</Text>
      </View>
      <View style={[styles.section, { backgroundColor: c.surface }]}>
        <View style={[styles.row, { borderBottomColor: c.border }]}>
          <Text style={[styles.label, { color: c.textSecondary }]}>服务器</Text>
          <Text style={[styles.value, { color: c.text }]} numberOfLines={1}>{host}</Text>
        </View>
        <View style={styles.row}>
          <Text style={[styles.label, { color: c.text }]}>深色模式</Text>
          <Switch
            value={theme === 'dark'}
            onValueChange={(v) => setTheme(v ? 'dark' : 'light')}
            trackColor={{ true: c.accent, false: c.border }}
          />
        </View>
      </View>
      <View style={[styles.section, { backgroundColor: c.surface }]}>
        <Text style={[styles.sectionTitle, { color: c.textSecondary }]}>监控设置</Text>
        <View style={[styles.row, { borderBottomColor: c.border }]}>
          <Text style={[styles.label, { color: c.text }]}>自动监控</Text>
          <Switch value={!!config.auto_monitor} onValueChange={(v) => toggleConfig('auto_monitor', v)} trackColor={{ true: c.accent, false: c.border }} />
        </View>
        <View style={[styles.row, { borderBottomColor: c.border }]}>
          <Text style={[styles.label, { color: c.text }]}>自动确认</Text>
          <Switch value={!!config.auto_yes} onValueChange={(v) => toggleConfig('auto_yes', v)} trackColor={{ true: c.accent, false: c.border }} />
        </View>
        <View style={[styles.row, { borderBottomColor: c.border }]}>
          <Text style={[styles.label, { color: c.text }]}>截屏间隔</Text>
          <Text style={[styles.value, { color: c.text }]}>{config.screenshot_interval || 15}s</Text>
        </View>
        <View style={styles.row}>
          <Text style={[styles.label, { color: c.text }]}>流模式</Text>
          <Switch value={!!config.stream_mode} onValueChange={(v) => toggleConfig('stream_mode', v)} trackColor={{ true: c.accent, false: c.border }} />
        </View>
      </View>
      <TouchableOpacity style={[styles.logout, { backgroundColor: c.danger }]} onPress={handleLogout}>
        <Text style={styles.logoutText}>断开连接</Text>
      </TouchableOpacity>
      <Text style={[styles.version, { color: c.textSecondary }]}>BedCode v1.0.0</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  section: { marginTop: 12, borderRadius: 12, marginHorizontal: 16, overflow: 'hidden' },
  sectionTitle: { fontSize: 12, fontWeight: '600', paddingHorizontal: 16, paddingVertical: 8, textTransform: 'uppercase' },
  headerBar: { paddingTop: 50, paddingBottom: 14, paddingHorizontal: 16 },
  header: { fontSize: 18, fontWeight: '600' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: StyleSheet.hairlineWidth },
  label: { fontSize: 14 },
  value: { fontSize: 14, flex: 1, textAlign: 'right', marginLeft: 12 },
  logout: { margin: 16, height: 46, borderRadius: 12, marginHorizontal: 16, justifyContent: 'center', alignItems: 'center' },
  logoutText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  version: { textAlign: 'center', fontSize: 12, marginTop: 8, marginBottom: 32 },
});
