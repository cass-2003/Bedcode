import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

export default function StatusHeader({ onAction }: { onAction?: () => void }) {
  const insets = useSafeAreaInsets();
  const { theme, claudeState, windowTitle, windowLabel, thinkingStart, connected } = useChatStore();
  const c = Colors[theme];
  const router = useRouter();
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

  const fmt = elapsed >= 60 ? `${Math.floor(elapsed / 60)}m${String(elapsed % 60).padStart(2, '0')}s` : `${elapsed}s`;
  const stateText =
    claudeState === 'thinking' ? `thinking ${fmt}` :
    claudeState === 'idle' ? 'idle' : 'connecting...';

  const name = windowLabel || windowTitle || 'Claude Code';
  const avatarChar = name.charAt(0).toUpperCase();
  const stateColor = claudeState === 'thinking' ? '#E8A838' : connected ? '#4DCA65' : '#999';

  return (
    <BlurView intensity={25} tint={theme === 'dark' ? 'dark' : 'light'} style={[styles.container, { height: insets.top + 50, paddingTop: insets.top }]}>
      <View style={styles.row}>
        <Pressable onPress={() => router.navigate('/(tabs)/windows')} style={styles.backBtn} hitSlop={8}>
          <Text style={[styles.backArrow, { color: c.headerText }]}>{'\u276E'}</Text>
        </Pressable>

        <Pressable style={styles.center} onPress={onAction}>
          <Text style={[styles.title, { color: c.headerText }]} numberOfLines={1}>{name}</Text>
          <Text style={[styles.subtitle, { color: stateColor }]} numberOfLines={1}>{stateText}</Text>
        </Pressable>

        <Pressable onPress={onAction} style={styles.avatarWrap}>
          <View style={[styles.avatar, { backgroundColor: '#5BA0D0' }]}>
            <Text style={styles.avatarLetter}>{avatarChar}</Text>
          </View>
          <View style={[styles.onlineDot, { backgroundColor: connected ? '#4DCA65' : '#999', borderColor: 'transparent' }]} />
        </Pressable>
      </View>
    </BlurView>
  );
}

const styles = StyleSheet.create({
  container: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10 },
  row: { height: 50, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8 },
  backBtn: { width: 40, alignItems: 'center', justifyContent: 'center' },
  backArrow: { fontSize: 22, fontWeight: '300' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 16, fontWeight: '600' },
  subtitle: { fontSize: 12, marginTop: 1 },
  avatarWrap: { width: 40, alignItems: 'center', justifyContent: 'center' },
  avatar: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 16, fontWeight: '700' },
  onlineDot: { position: 'absolute', bottom: 4, right: 2, width: 10, height: 10, borderRadius: 5, borderWidth: 2 },
});
