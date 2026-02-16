import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, Pressable, FlatList, Modal, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = { visible: boolean; onClose: () => void };

async function apiFetch(path: string, options?: RequestInit) {
  const { host, token } = useChatStore.getState();
  if (!host || !token) return null;
  const res = await fetch(`${host}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(options?.headers || {}) },
  });
  return res.ok ? res.json() : null;
}

export default function BatchPanel({ visible, onClose }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const [queue, setQueue] = useState<any[]>([]);
  const [input, setInput] = useState('');

  const refresh = async () => {
    const data = await apiFetch('/api/queue');
    if (data) setQueue(Array.isArray(data) ? data : data.queue ?? []);
  };

  useEffect(() => { if (visible) refresh(); }, [visible]);

  const handleClear = async () => {
    await apiFetch('/api/queue', { method: 'DELETE' });
    await refresh();
    onClose();
  };

  const handleSend = async () => {
    const messages = input.split('|').map((s) => s.trim()).filter(Boolean);
    if (!messages.length) return;
    await apiFetch('/api/batch', { method: 'POST', body: JSON.stringify({ messages }) });
    setInput('');
    await refresh();
    onClose();
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <View style={[styles.sheet, { backgroundColor: c.surface }]} onStartShouldSetResponder={() => true}>
          <View style={styles.header}>
            <Text style={[styles.title, { color: c.text }]}>Batch Queue</Text>
            <Pressable onPress={handleClear}><Text style={{ color: c.danger }}>Clear</Text></Pressable>
          </View>
          <FlatList
            data={queue}
            keyExtractor={(_, i) => String(i)}
            style={styles.list}
            renderItem={({ item }) => (
              <Text style={[styles.item, { color: c.text, backgroundColor: c.inputField }]}>
                {typeof item === 'string' ? item : item.message ?? JSON.stringify(item)}
              </Text>
            )}
            ListEmptyComponent={<Text style={{ color: c.textSecondary, textAlign: 'center', marginTop: 20 }}>Queue empty</Text>}
          />
          <TextInput
            style={[styles.input, { backgroundColor: c.inputField, color: c.text }]}
            value={input}
            onChangeText={setInput}
            placeholder="msg1 | msg2 | msg3"
            placeholderTextColor={c.textSecondary}
          />
          <Pressable style={[styles.sendBtn, { backgroundColor: c.accent }]} onPress={handleSend}>
            <Text style={styles.sendText}>Send Batch</Text>
          </Pressable>
        </View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '70%' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  title: { fontSize: 16, fontWeight: '600' },
  list: { maxHeight: 200 },
  item: { padding: 10, borderRadius: 8, marginBottom: 6, fontSize: 14 },
  input: { height: 40, borderRadius: 12, paddingHorizontal: 12, fontSize: 14, marginTop: 8 },
  sendBtn: { height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginTop: 10, marginBottom: 16 },
  sendText: { color: '#fff', fontWeight: '600', fontSize: 14 },
});
