import React, { useState, useRef } from 'react';
import { View, Text, Pressable, TextInput, ScrollView, Modal, Animated, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = {
  visible: boolean;
  onClose: () => void;
  onAction: (action: string) => void;
  onShell: (cmd: string) => void;
  onKeys: (keys: string[]) => void;
};

const quickActions = [
  { icon: '\u{1F4F8}', label: '截屏', action: 'screenshot' },
  { icon: '\u26D4', label: '中断', action: 'interrupt' },
  { icon: '\u21A9\uFE0F', label: '撤销', action: 'undo' },
  { icon: '\u{1F4CB}', label: 'Grab', action: 'grab' },
  { icon: '\u{1F4B0}', label: '费用', action: 'cost' },
  { icon: '\u{1F4E4}', label: '导出', action: 'export' },
  { icon: '\u{1F4CE}', label: '剪贴板', action: 'clipboard' },
];

const keyButtons = [
  { label: 'Y', keys: ['y', 'enter'] },
  { label: 'N', keys: ['n', 'enter'] },
  { label: '1', keys: ['1', 'enter'] },
  { label: '2', keys: ['2', 'enter'] },
  { label: '3', keys: ['3', 'enter'] },
  { label: '\u2191', keys: ['up'] },
  { label: '\u2193', keys: ['down'] },
  { label: '\u21B5', keys: ['enter'] },
  { label: 'Esc', keys: ['esc'] },
  { label: 'Tab', keys: ['tab'] },
];

export default function CommandBar({ visible, onClose, onAction, onShell, onKeys }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const [shellCmd, setShellCmd] = useState('');
  const slideAnim = useRef(new Animated.Value(400)).current;

  React.useEffect(() => {
    Animated.spring(slideAnim, {
      toValue: visible ? 0 : 400,
      useNativeDriver: true,
      friction: 9,
      tension: 65,
    }).start();
  }, [visible]);

  const handleShell = () => {
    const cmd = shellCmd.trim();
    if (!cmd) return;
    onShell(cmd);
    setShellCmd('');
    onClose();
  };

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Animated.View
          style={[styles.sheet, { backgroundColor: c.surface, transform: [{ translateY: slideAnim }] }]}
          onStartShouldSetResponder={() => true}
        >
          <View style={styles.handle} />

          <Text style={[styles.sectionLabel, { color: c.textSecondary }]}>快捷操作</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.quickRow}>
            {quickActions.map((a) => (
              <Pressable key={a.action} style={styles.quickItem} onPress={() => { onAction(a.action); onClose(); }}>
                <View style={[styles.quickCircle, { backgroundColor: c.accent }]}>
                  <Text style={styles.quickIcon}>{a.icon}</Text>
                </View>
                <Text style={[styles.quickLabel, { color: c.textSecondary }]}>{a.label}</Text>
              </Pressable>
            ))}
          </ScrollView>

          <Text style={[styles.sectionLabel, { color: c.textSecondary }]}>按键面板</Text>
          <View style={styles.keyGrid}>
            {keyButtons.map((k) => (
              <Pressable
                key={k.label}
                style={[styles.keyBtn, { backgroundColor: c.inputField }]}
                onPress={() => { onKeys(k.keys); onClose(); }}
              >
                <Text style={[styles.keyText, { color: c.text }]}>{k.label}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={[styles.sectionLabel, { color: c.textSecondary }]}>Shell 命令</Text>
          <View style={styles.shellRow}>
            <Text style={[styles.shellPrefix, { color: c.accent }]}>!</Text>
            <TextInput
              style={[styles.shellInput, { backgroundColor: c.inputField, color: c.text }]}
              value={shellCmd}
              onChangeText={setShellCmd}
              placeholder="ls -la"
              placeholderTextColor={c.textSecondary}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Pressable style={[styles.shellRun, { backgroundColor: c.accent }]} onPress={handleShell}>
              <Text style={styles.shellRunText}>{'\u25B6'}</Text>
            </Pressable>
          </View>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { borderTopLeftRadius: 14, borderTopRightRadius: 14, paddingTop: 8, paddingBottom: 36, paddingHorizontal: 16, maxHeight: '70%' },
  handle: { width: 36, height: 4, borderRadius: 2, backgroundColor: '#8E8E93', alignSelf: 'center', marginBottom: 12 },
  sectionLabel: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', marginTop: 12, marginBottom: 8 },
  quickRow: { marginBottom: 4 },
  quickItem: { alignItems: 'center', marginRight: 16 },
  quickCircle: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  quickIcon: { fontSize: 22, color: '#fff' },
  quickLabel: { fontSize: 11, marginTop: 4 },
  keyGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  keyBtn: { width: 52, height: 40, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  keyText: { fontSize: 15, fontWeight: '500' },
  shellRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  shellPrefix: { fontSize: 18, fontWeight: '700' },
  shellInput: { flex: 1, height: 38, borderRadius: 8, paddingHorizontal: 10, fontSize: 14 },
  shellRun: { width: 38, height: 38, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  shellRunText: { color: '#fff', fontSize: 16 },
});
