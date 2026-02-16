import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, TextInput, Pressable, FlatList, Modal, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = { visible: boolean; onClose: () => void; onSend: (text: string) => void; initialSearch?: string };

async function apiFetch(path: string) {
  const { host, token } = useChatStore.getState();
  if (!host || !token) return null;
  const res = await fetch(`${host}${path}`, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  });
  return res.ok ? res.json() : null;
}

export default function HistoryPanel({ visible, onClose, onSend, initialSearch = '' }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const [history, setHistory] = useState<any[]>([]);
  const [search, setSearch] = useState(initialSearch);

  const refresh = useCallback(async () => {
    const data = await apiFetch('/api/history');
    if (data) setHistory(Array.isArray(data) ? data : data.history ?? []);
  }, []);

  useEffect(() => {
    if (visible) { refresh(); setSearch(initialSearch); }
  }, [visible]);

  const getText = (item: any) => (typeof item === 'string' ? item : item.text ?? item.message ?? '');
  const filtered = history.filter((item) => getText(item).toLowerCase().includes(search.toLowerCase()));

  const handleTap = (item: any) => { onSend(getText(item)); onClose(); };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <View style={[styles.sheet, { backgroundColor: c.surface }]} onStartShouldSetResponder={() => true}>
          <Text style={[styles.title, { color: c.text }]}>History</Text>
          <TextInput
            style={[styles.search, { backgroundColor: c.inputField, color: c.text }]}
            value={search}
            onChangeText={setSearch}
            placeholder="Search..."
            placeholderTextColor={c.textSecondary}
            autoCapitalize="none"
          />
          <FlatList
            data={filtered}
            keyExtractor={(_, i) => String(i)}
            style={styles.list}
            onRefresh={refresh}
            refreshing={false}
            renderItem={({ item }) => (
              <Pressable onPress={() => handleTap(item)}>
                <Text style={[styles.item, { color: c.text, backgroundColor: c.inputField }]} numberOfLines={2}>
                  {getText(item)}
                </Text>
              </Pressable>
            )}
            ListEmptyComponent={<Text style={{ color: c.textSecondary, textAlign: 'center', marginTop: 20 }}>No results</Text>}
          />
        </View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '70%' },
  title: { fontSize: 16, fontWeight: '600', marginBottom: 12 },
  search: { height: 40, borderRadius: 12, paddingHorizontal: 12, fontSize: 14, marginBottom: 8 },
  list: { maxHeight: 300 },
  item: { padding: 10, borderRadius: 8, marginBottom: 6, fontSize: 14 },
});
