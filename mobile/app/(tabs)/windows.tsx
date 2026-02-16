import { useCallback, useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert, Platform, TextInput, Pressable, Modal } from 'react-native';
import { useChatStore } from '../../stores/chatStore';
import { Colors } from '../../constants/theme';
import { useApi } from '../../hooks/useApi';
import { useRouter } from 'expo-router';

const fmtTime = (ts: number) => {
  const d = new Date(ts);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return d.toTimeString().slice(0, 5);
  if (now.getTime() - d.getTime() < 7 * 86400000) return ['日','一','二','三','四','五','六'][d.getDay()];
  return `${d.getMonth() + 1}/${d.getDate()}`;
};

export default function WindowsScreen() {
  const { windows, theme, setWindows, messagesByHandle, unreadByHandle, windowStates } = useChatStore();
  const api = useApi();
  const router = useRouter();
  const c = Colors[theme];

  const refresh = useCallback(async () => {
    const res = await api.getWindows();
    const list = res.data?.windows ?? res.data;
    if (res.ok && Array.isArray(list)) setWindows(list);
  }, []);

  useEffect(() => { refresh(); }, []);

  const onTap = useCallback(async (handle: number) => {
    await api.setTarget(handle);
    await useChatStore.getState().setCurrentHandle(handle);
    router.navigate('/(tabs)/');
  }, []);

  const [editingHandle, setEditingHandle] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  const editLabel = useCallback((handle: number, currentLabel: string) => {
    if (Platform.OS === 'ios') {
      Alert.prompt('编辑标签', '输入新标签', [
        { text: '取消', style: 'cancel' },
        { text: '确定', onPress: async (label) => { await api.setLabel(handle, label || ''); refresh(); } },
      ], 'plain-text', currentLabel);
    } else {
      setEditText(currentLabel);
      setEditingHandle(handle);
    }
  }, [refresh]);

  const submitLabel = useCallback(async () => {
    if (editingHandle == null) return;
    await api.setLabel(editingHandle, editText);
    setEditingHandle(null);
    refresh();
  }, [editingHandle, editText, refresh]);

  return (
    <View style={[styles.container, { backgroundColor: c.background }]}>
      <View style={[styles.headerBar, { backgroundColor: c.headerBg }]}>
        <Text style={[styles.header, { color: c.headerText }]}>Claude 窗口</Text>
      </View>
      <FlatList
        data={windows}
        keyExtractor={(w) => String(w.handle)}
        refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor={c.accent} />}
        renderItem={({ item }) => {
          const msgs = messagesByHandle[item.handle];
          const last = msgs?.length ? msgs[msgs.length - 1] : null;
          const unread = unreadByHandle[item.handle] || 0;
          const state = windowStates[item.handle] || item.state;
          const name = item.label || item.title || `窗口 ${item.handle}`;
          const avatar = name.charAt(0).toUpperCase();

          return (
            <TouchableOpacity
              style={[styles.row, { borderBottomColor: c.border }]}
              onPress={() => onTap(item.handle)}
              onLongPress={() => editLabel(item.handle, item.label || '')}
              activeOpacity={0.6}
            >
              {/* Avatar */}
              <View style={[styles.avatar, { backgroundColor: c.bubbleSent }]}>
                <Text style={[styles.avatarText, { color: c.text }]}>{avatar}</Text>
                <View style={[
                  styles.statusDot,
                  { backgroundColor: state === 'thinking' ? c.warning : c.success, borderColor: c.background },
                ]} />
              </View>

              {/* Middle: name + preview */}
              <View style={styles.mid}>
                <Text style={[styles.name, { color: c.text }]} numberOfLines={1}>{name}</Text>
                <Text style={[styles.preview, { color: c.textSecondary }]} numberOfLines={1}>
                  {last ? last.text : '暂无消息'}
                </Text>
              </View>

              {/* Right: time + unread */}
              <View style={styles.right}>
                {last && <Text style={[styles.time, { color: c.textSecondary }]}>{fmtTime(last.timestamp)}</Text>}
                {unread > 0 && (
                  <View style={[styles.unread, { backgroundColor: c.danger }]}>
                    <Text style={styles.unreadText}>{unread > 99 ? '99+' : unread}</Text>
                  </View>
                )}
              </View>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={<Text style={[styles.empty, { color: c.textSecondary }]}>暂无窗口</Text>}
      />
      <Modal visible={editingHandle != null} transparent animationType="fade" onRequestClose={() => setEditingHandle(null)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalBox, { backgroundColor: c.surface }]}>
            <Text style={[styles.modalTitle, { color: c.text }]}>编辑标签</Text>
            <TextInput style={[styles.modalInput, { color: c.text, borderColor: c.textSecondary }]} value={editText} onChangeText={setEditText} autoFocus placeholder="输入新标签" placeholderTextColor={c.textSecondary} />
            <View style={styles.modalButtons}>
              <Pressable onPress={() => setEditingHandle(null)}><Text style={{ color: c.textSecondary }}>取消</Text></Pressable>
              <Pressable onPress={submitLabel}><Text style={{ color: c.accent, fontWeight: '600' }}>确定</Text></Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  headerBar: { paddingTop: 50, paddingBottom: 14, paddingHorizontal: 16 },
  header: { fontSize: 18, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth },
  avatar: { width: 50, height: 50, borderRadius: 25, justifyContent: 'center', alignItems: 'center' },
  avatarText: { fontSize: 20, fontWeight: '600' },
  statusDot: { position: 'absolute', bottom: 1, right: 1, width: 12, height: 12, borderRadius: 6, borderWidth: 2 },
  mid: { flex: 1, marginHorizontal: 12, justifyContent: 'center' },
  name: { fontSize: 16, fontWeight: '600', marginBottom: 3 },
  preview: { fontSize: 14 },
  right: { alignItems: 'flex-end', justifyContent: 'space-between', height: 44 },
  time: { fontSize: 12 },
  unread: { minWidth: 20, height: 20, borderRadius: 10, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 5, marginTop: 4 },
  unreadText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  empty: { textAlign: 'center', marginTop: 60, fontSize: 14 },
  modalOverlay: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)' },
  modalBox: { width: '80%', borderRadius: 12, padding: 20 },
  modalTitle: { fontSize: 16, fontWeight: '600', marginBottom: 12 },
  modalInput: { borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 16 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 20 },
});
