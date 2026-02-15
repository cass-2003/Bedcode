import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

export default function ThinkingIndicator() {
  const theme = useChatStore((s) => s.theme);
  const claudeState = useChatStore((s) => s.claudeState);
  const c = Colors[theme];

  const dots = [
    { scale: useRef(new Animated.Value(1)).current, opacity: useRef(new Animated.Value(0.4)).current },
    { scale: useRef(new Animated.Value(1)).current, opacity: useRef(new Animated.Value(0.4)).current },
    { scale: useRef(new Animated.Value(1)).current, opacity: useRef(new Animated.Value(0.4)).current },
  ];

  useEffect(() => {
    if (claudeState !== 'thinking') return;
    const anims = dots.map((dot, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 180),
          Animated.parallel([
            Animated.timing(dot.scale, { toValue: 1.4, duration: 250, useNativeDriver: true }),
            Animated.timing(dot.opacity, { toValue: 1, duration: 250, useNativeDriver: true }),
          ]),
          Animated.parallel([
            Animated.timing(dot.scale, { toValue: 1, duration: 250, useNativeDriver: true }),
            Animated.timing(dot.opacity, { toValue: 0.4, duration: 250, useNativeDriver: true }),
          ]),
        ])
      )
    );
    anims.forEach((a) => a.start());
    return () => anims.forEach((a) => a.stop());
  }, [claudeState]);

  if (claudeState !== 'thinking') return null;

  return (
    <View style={styles.row}>
      <View style={[styles.bubble, { backgroundColor: c.bubbleRecv }]}>
        {dots.map((dot, i) => (
          <Animated.View
            key={i}
            style={[styles.dot, { backgroundColor: c.accent, opacity: dot.opacity, transform: [{ scale: dot.scale }] }]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', paddingHorizontal: 8, marginVertical: 4 },
  bubble: {
    flexDirection: 'row',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 18,
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 6,
  },
  dot: { width: 7, height: 7, borderRadius: 3.5 },
});
