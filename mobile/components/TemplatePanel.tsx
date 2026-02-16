import React from 'react';
import { Modal, View, Text, Pressable, FlatList, Alert, StyleSheet } from 'react-native';
import { useChatStore } from '../stores/chatStore';
import { Colors } from '../constants/theme';

type Props = {
  visible: boolean;
  onClose: () => void;
  onSend: (text: string) => void;
};

export default function TemplatePanel({ visible, onClose, onSend }: Props) {
  const theme = useChatStore((s) => s.theme);
  const templates = useChatStore((s) => s.templates);
  const setTemplates = useChatStore((s) => s.setTemplates);
  const c = Colors[theme];

  const entries = Object.entries(templates);

  const handleAdd = () => {
    Alert.prompt('Template Name', 'Enter a name for this template:', (name) => {
      if (!name?.trim()) return;
      Alert.prompt('Template Content', `Content for "${name}":`, (content) => {
        if (!content?.trim()) return;
        setTemplates({ ...templates, [name.trim()]: content.trim() });
      });
    });
  };

  const handleDelete = (name: string) => {
    Alert.alert('Delete Template', `Delete "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive', onPress: () => {
          const next = { ...templates };
          delete next[name];
          setTemplates(next);
        },
      },
    ]);
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={[styles.overlay, { backgroundColor: c.background }]}>
        <View style={[styles.header, { borderBottomColor: c.border }]}>
          <Text style={[styles.title, { color: c.text }]}>Templates</Text>
          <View style={{ flexDirection: 'row', gap: 16 }}>
            <Pressable onPress={handleAdd}>
              <Text style={[styles.btn, { color: c.accent }]}>+ Add</Text>
            </Pressable>
            <Pressable onPress={onClose}>
              <Text style={[styles.btn, { color: c.textSecondary }]}>Close</Text>
            </Pressable>
          </View>
        </View>
        {entries.length === 0 ? (
          <Text style={[styles.empty, { color: c.textSecondary }]}>No templates yet</Text>
        ) : (
          <FlatList
            data={entries}
            keyExtractor={([name]) => name}
            renderItem={({ item: [name, content] }) => (
              <Pressable
                style={[styles.item, { backgroundColor: c.surface, borderBottomColor: c.border }]}
                onPress={() => { onSend(content); onClose(); }}
                onLongPress={() => handleDelete(name)}
              >
                <Text style={[styles.itemName, { color: c.text }]}>{name}</Text>
                <Text style={[styles.itemPreview, { color: c.textSecondary }]} numberOfLines={1}>{content}</Text>
              </Pressable>
            )}
          />
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, paddingTop: 50 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1 },
  title: { fontSize: 18, fontWeight: '600' },
  btn: { fontSize: 15, fontWeight: '500' },
  empty: { textAlign: 'center', marginTop: 40, fontSize: 14 },
  item: { paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth },
  itemName: { fontSize: 15, fontWeight: '500', marginBottom: 2 },
  itemPreview: { fontSize: 13 },
});
