import { useCallback, useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, Pressable, StyleSheet, RefreshControl, Alert } from 'react-native';
import { useChatStore } from '../../stores/chatStore';
import { Colors } from '../../constants/theme';
import { useApi } from '../../hooks/useApi';

export default function HistoryScreen() {
  const { theme, addMessage } = useChatStore();
  const api = useApi();
  const c = Colors[theme];
  const [history, setHistory] = useState<string[]>([]);
  const [queue, setQueue] = useState<{index: number; text: string}[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    const [h, q] = await Promise.all([api.getHistory(), api.getQueue()]);
    if (h.ok) setHistory(h.data?.items || []);
    if (q.ok) setQueue(q.data?.items || []);
    setRefreshing(false);
  }, []);

  useEffect(() => { load(); }, []);

  const resend = useCallback(async (text: string) => {
    const id = Date.now().toString();
    addMessage({ id, type: 'sent', text, timestamp: Date.now(), status: 'sending' });
    const res = await api.sendMessage(text);
    const st = !res.ok ? 'failed' : res.data?.status === 'queued' ? 'queued' : res.data?.status === 'error' ? 'failed' : 'sent';
    useChatStore.getState().updateMessageStatus(id, st);
  }, []);

  const deleteQueueItem = useCallback(async (index: number) => {
    Alert.alert('删除', `确认删除第 ${index + 1} 条？`, [
      { text: '取消', style: 'cancel' },
      { text: '删除', style: 'destructive', onPress: load },
    ]);
  }, []);

  const clearQueue = useCallback(async () => {
    const res = await api.clearQueue();
    if (res.ok) { setQueue([]); }
    else Alert.alert('错误', res.error || '清空失败');
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: c.background }]}>
      <View style={[styles.headerBar, { backgroundColor: c.headerBg }]}>
        <Text style={[styles.header, { color: c.headerText }]}>历史 & 队列</Text>
      </View>
      <FlatList
        data={[...queue.map((q) => ({ ...q, _type: 'queue' as const })), ...history.map((h, i) => ({ index: i, text: h, _type: 'history' as const }))]}
        keyExtractor={(item, i) => `${item._type}-${i}`}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} tintColor={c.accent} />}
        ListHeaderComponent={
          queue.length > 0 ? (
            <View style={[styles.sectionHeader, { borderBottomColor: c.border }]}>
              <Text style={[styles.sectionTitle, { color: c.accent }]}>消息队列 ({queue.length})</Text>
              <TouchableOpacity onPress={clearQueue}>
                <Text style={{ color: c.danger, fontSize: 13 }}>清空</Text>
              </TouchableOpacity>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <View style={[styles.item, { backgroundColor: c.surface }]}>
            <Text style={[styles.itemText, { color: c.text }]} numberOfLines={2}>{item.text}</Text>
            <Pressable
              style={[styles.itemBtn, { backgroundColor: item._type === 'queue' ? c.danger : c.accent }]}
              onPress={() => item._type === 'queue' ? deleteQueueItem(item.index) : resend(item.text)}
            >
              <Text style={styles.itemBtnText}>{item._type === 'queue' ? '删除' : '重发'}</Text>
            </Pressable>
          </View>
        )}
        ListEmptyComponent={<Text style={[styles.empty, { color: c.textSecondary }]}>暂无记录</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  headerBar: { paddingTop: 50, paddingBottom: 14, paddingHorizontal: 16 },
  header: { fontSize: 18, fontWeight: '600' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12, marginHorizontal: 12, marginTop: 8, borderBottomWidth: StyleSheet.hairlineWidth },
  sectionTitle: { fontSize: 14, fontWeight: '600' },
  item: { flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 12, marginHorizontal: 12, marginVertical: 3 },
  itemText: { flex: 1, fontSize: 14, marginRight: 8 },
  itemBtn: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 14 },
  itemBtnText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  empty: { textAlign: 'center', marginTop: 60, fontSize: 14 },
});
