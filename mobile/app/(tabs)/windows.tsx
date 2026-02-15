import { useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native';
import { useChatStore } from '../../stores/chatStore';
import { Colors } from '../../constants/theme';
import { useApi } from '../../hooks/useApi';

export default function WindowsScreen() {
  const { windows, theme } = useChatStore();
  const api = useApi();
  const c = Colors[theme];

  const refresh = useCallback(async () => { await api.getWindows(); }, []);

  const switchWindow = useCallback(async (handle: number) => {
    await api.setTarget(handle);
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: c.background }]}>
      <View style={[styles.headerBar, { backgroundColor: c.headerBg }]}>
        <Text style={[styles.header, { color: c.headerText }]}>Claude 窗口</Text>
      </View>
      <FlatList
        data={windows}
        keyExtractor={(w) => String(w.handle)}
        refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor={c.accent} />}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[
              styles.item,
              { backgroundColor: item.current ? c.bubbleSent : c.surface },
              item.current && { borderLeftWidth: 3, borderLeftColor: c.accent },
            ]}
            onPress={() => switchWindow(item.handle)}
          >
            <Text style={[styles.title, { color: c.text }]} numberOfLines={1}>
              🪟 {item.title}
            </Text>
            <View style={styles.row}>
              <View style={[styles.badge, { backgroundColor: item.state === 'thinking' ? c.warning : c.success }]}>
                <Text style={styles.badgeText}>{item.state}</Text>
              </View>
              {item.label ? <Text style={[styles.label, { color: c.textSecondary }]}>{item.label}</Text> : null}
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={[styles.empty, { color: c.textSecondary }]}>暂无窗口</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  headerBar: { paddingTop: 50, paddingBottom: 14, paddingHorizontal: 16 },
  header: { fontSize: 18, fontWeight: '600' },
  item: { padding: 14, borderRadius: 12, marginHorizontal: 12, marginVertical: 3 },
  title: { fontSize: 16, fontWeight: '500', marginBottom: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  badge: { paddingHorizontal: 10, paddingVertical: 2, borderRadius: 6 },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  label: { fontSize: 12 },
  empty: { textAlign: 'center', marginTop: 60, fontSize: 14 },
});
