import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

export default function StatusHeader({ onAction }: { onAction?: () => void }) {
  const insets = useSafeAreaInsets();
  const { theme, claudeState, windowTitle, windowLabel, thinkingStart, connected } = useChatStore();
  const c = Colors[theme];
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (claudeState !== 'thinking' || !thinkingStart) {
      setElapsed(0);
      return;
    }
    setElapsed(Math.floor((Date.now() - thinkingStart) / 1000));
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - thinkingStart) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [claudeState, thinkingStart]);

  const stateText =
    claudeState === 'thinking' ? `thinking ${elapsed}s` :
    claudeState === 'idle' ? 'idle' : 'unknown';

  const subtitle = windowLabel || windowTitle || '';

  return (
    <View style={[styles.container, { backgroundColor: c.headerBg, paddingTop: insets.top }]}>
      <View style={styles.row}>
        <View style={styles.left}>
          <View style={[styles.avatar, { backgroundColor: c.accent }]}>
            <Text style={styles.avatarLetter}>C</Text>
            <View style={[styles.onlineDot, { backgroundColor: connected ? c.success : c.danger, borderColor: c.headerBg }]} />
          </View>
          <View style={styles.titles}>
            <Text style={[styles.title, { color: c.headerText }]}>Claude Code</Text>
            <Text style={[styles.subtitle, { color: 'rgba(255,255,255,0.6)' }]} numberOfLines={1}>
              {subtitle ? `${subtitle} \u00B7 ` : ''}{stateText}
            </Text>
          </View>
        </View>
        {onAction && (
          <Pressable onPress={onAction} style={styles.actionBtn}>
            <Text style={[styles.actionIcon, { color: c.headerText }]}>{'\u26A1'}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  row: { height: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14 },
  left: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  avatar: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 18, fontWeight: '700' },
  onlineDot: { position: 'absolute', bottom: 0, right: 0, width: 8, height: 8, borderRadius: 4, borderWidth: 1.5 },
  titles: { marginLeft: 12, flex: 1 },
  title: { fontSize: 17, fontWeight: '600' },
  subtitle: { fontSize: 13, marginTop: 1 },
  actionBtn: { padding: 8 },
  actionIcon: { fontSize: 24 },
});
