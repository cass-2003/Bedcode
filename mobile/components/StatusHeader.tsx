import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
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
    <BlurView intensity={80} tint={theme === 'dark' ? 'dark' : 'light'} style={[styles.container, { paddingTop: insets.top }]}>
      <View style={[styles.row, { backgroundColor: theme === 'dark' ? 'rgba(23,33,43,0.65)' : 'rgba(81,125,162,0.65)' }]}>
        <View style={styles.left}>
          <View style={[styles.avatarRing, { borderColor: c.accent }]}>
            <View style={[styles.avatar, { backgroundColor: c.accent }]}>
              <Text style={styles.avatarLetter}>C</Text>
              <View style={[styles.onlineDot, { backgroundColor: connected ? c.success : c.danger, borderColor: c.headerBg }]} />
            </View>
          </View>
          <View style={styles.titles}>
            <Text style={[styles.title, { color: c.headerText }]}>Claude Code</Text>
            <Text style={[styles.subtitle, { color: c.tabInactive }]} numberOfLines={1}>
              {subtitle ? `${subtitle} \u00B7 ` : ''}{stateText}
            </Text>
          </View>
        </View>
        {onAction && (
          <Pressable onPress={onAction} style={styles.actionBtn}>
            <Text style={[styles.actionIcon, { color: c.headerText }]}>{'\u2630'}</Text>
          </Pressable>
        )}
      </View>
    </BlurView>
  );
}

const styles = StyleSheet.create({
  container: {},
  row: { height: 52, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14 },
  left: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  avatar: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  avatarRing: { borderWidth: 2, borderRadius: 23, padding: 1 },
  avatarLetter: { color: '#fff', fontSize: 18, fontWeight: '700' },
  onlineDot: { position: 'absolute', bottom: 0, right: 0, width: 10, height: 10, borderRadius: 5, borderWidth: 2 },
  titles: { marginLeft: 12, flex: 1 },
  title: { fontSize: 17, fontWeight: '600' },
  subtitle: { fontSize: 13, marginTop: 1 },
  actionBtn: { padding: 8 },
  actionIcon: { fontSize: 22 },
});
