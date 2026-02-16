import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

const defaultButtons = [
  { icon: '\u{1F4F7}', label: '截屏', action: 'screenshot' },
  { icon: '\u{1FA9F}', label: '窗口', action: 'window' },
  { icon: '\u{1F440}', label: '监控', action: 'toggle_monitor' },
  { icon: '\u23F9', label: '停止', action: 'interrupt' },
  { icon: '\u{1F504}', label: '状态', action: 'grab' },
  { icon: '\u{1F4CB}', label: '剪贴板', action: 'clipboard' },
  { icon: '\u{1F4DD}', label: '模板', action: 'templates' },
];

type Props = { onAction: (action: string) => void };

export default function ActionBar({ onAction }: Props) {
  const theme = useChatStore((s) => s.theme);
  const autoMonitor = useChatStore((s) => s.autoMonitor);
  const customButtons = useChatStore((s) => s.customButtons);
  const c = Colors[theme];
  const btns = customButtons.length > 0 ? customButtons : defaultButtons;

  return (
    <View style={[styles.container, { borderTopColor: c.border }]}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {btns.map((b) => {
          const active = b.action === 'toggle_monitor' && autoMonitor;
          return (
            <Pressable
              key={b.action}
              style={[styles.btn, { backgroundColor: active ? c.accent : c.actionBg }]}
              onPress={() => onAction(b.action)}
            >
              <Text style={styles.icon}>{b.icon}</Text>
              <Text style={[styles.label, { color: active ? '#fff' : c.actionText }]}>{b.label}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { borderTopWidth: StyleSheet.hairlineWidth, paddingVertical: 4 },
  scroll: { paddingHorizontal: 8, gap: 6 },
  btn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 16, gap: 4 },
  icon: { fontSize: 14 },
  label: { fontSize: 12, fontWeight: '500' },
});
