import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  Image,
  Alert,
  Animated,
  Pressable,
  StyleSheet,
  Dimensions,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = {
  id: string;
  type: 'sent' | 'recv' | 'system' | 'screenshot' | 'prompt';
  text: string;
  timestamp: number;
  status?: string;
  imageBase64?: string;
  imageUri?: string;
  actions?: Array<{label: string; action?: string; keys?: string}>;
  showSender?: boolean;
  onAction?: (action: string, keys?: string) => void;
};

const SCREEN_W = Dimensions.get('window').width;

const statusIcon: Record<string, string> = {
  sending: '\u{1F550}',
  sent: '\u2713',
  injected: '\u2713\u2713',
  queued: '\u{1F4CB}',
  failed: '\u274C',
};

const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

export default function ChatBubble({ id, type, text, timestamp, status, imageBase64, imageUri, actions, showSender, onAction }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 150, useNativeDriver: true }).start();
  }, []);

  const handleLongPress = () => {
    Alert.alert('操作', undefined, [
      { text: 'Copy', onPress: () => Clipboard.setStringAsync(text) },
      { text: '取消', style: 'cancel' },
    ]);
  };

  const time = formatTime(timestamp);

  if (type === 'system') {
    return (
      <Animated.View style={[styles.systemWrap, { opacity: fadeAnim }]}>
        <View style={[styles.systemBubble, { backgroundColor: c.bubbleSystem }]}>
          <Text style={[styles.systemText, { color: c.textSecondary }]}>{text}</Text>
          {actions && actions.length > 0 && (
            <View style={styles.actionsRow}>
              {actions.map((a, i) => (
                <Pressable
                  key={i}
                  style={[styles.actionButton, { backgroundColor: c.accent }]}
                  onPress={() => onAction?.(a.action || 'qr', a.keys)}
                >
                  <Text style={styles.actionButtonText}>{a.label}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </View>
      </Animated.View>
    );
  }

  const isSent = type === 'sent';
  const isScreenshot = type === 'screenshot';
  const isPrompt = type === 'prompt';
  const bubbleBg = isSent ? c.bubbleSent : c.bubbleRecv;
  const timeColor = isSent ? c.timeSent : c.timeRecv;

  const statusEl = isSent && status ? (
    <Text style={[styles.statusText, { color: status === 'injected' || status === 'sent' ? c.accent : timeColor }]}>
      {' '}{statusIcon[status] ?? status}
    </Text>
  ) : null;

  return (
    <Animated.View
      style={[
        styles.row,
        { justifyContent: isSent ? 'flex-end' : 'flex-start', opacity: fadeAnim },
      ]}
    >
      <Pressable onLongPress={handleLongPress} style={styles.bubbleWrap}>
        <View
          style={[
            styles.bubble,
            { backgroundColor: bubbleBg },
            isSent
              ? { borderTopLeftRadius: 18, borderTopRightRadius: 18, borderBottomLeftRadius: 18, borderBottomRightRadius: 4 }
              : { borderTopLeftRadius: 4, borderTopRightRadius: 18, borderBottomLeftRadius: 18, borderBottomRightRadius: 18 },
          ]}
        >
          {(!isSent && !isScreenshot || isPrompt) && showSender !== false && (
            <Text style={[styles.senderName, { color: c.accent }]}>Claude</Text>
          )}

          {isSent && imageUri && (
            <Image source={{ uri: imageUri }} style={styles.sentImage} resizeMode="cover" />
          )}

          {isScreenshot && imageBase64 ? (
            <View>
              <Pressable onPress={() => console.log('screenshot tap', id)}>
                <Image
                  source={{ uri: `data:image/png;base64,${imageBase64}` }}
                  style={styles.screenshotImg}
                  resizeMode="cover"
                />
              </Pressable>
              <View style={styles.imgTimePill}>
                <Text style={styles.imgTimeText}>{time}</Text>
              </View>
            </View>
          ) : null}

          {text ? (
            <Text style={[styles.text, { color: c.text }]}>
              {text}
              <Text style={styles.timeInlineSpacer}>{'      '}{statusEl ? '    ' : ''}</Text>
            </Text>
          ) : null}

          {(!isScreenshot || text) && (
            <View style={styles.meta}>
              <Text style={[styles.time, { color: timeColor }]}>{time}</Text>
              {statusEl}
            </View>
          )}
          {actions && actions.length > 0 && (
            <View style={styles.actionsRow}>
              {actions.map((a, i) => (
                <Pressable
                  key={i}
                  style={[styles.actionButton, { backgroundColor: c.accent }]}
                  onPress={() => onAction?.(a.action || 'qr', a.keys)}
                >
                  <Text style={styles.actionButtonText}>{a.label}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', marginBottom: 2, paddingHorizontal: 8 },
  bubbleWrap: { maxWidth: SCREEN_W * 0.78 },
  bubble: {
    paddingHorizontal: 11,
    paddingTop: 7,
    paddingBottom: 5,
    minWidth: 60,
  },
  senderName: { fontSize: 13, fontWeight: '600', marginBottom: 2 },
  text: { fontSize: 15, lineHeight: 20 },
  timeInlineSpacer: { fontSize: 11, color: 'transparent' },
  meta: { flexDirection: 'row', alignSelf: 'flex-end', alignItems: 'center', marginTop: 1 },
  time: { fontSize: 11 },
  statusText: { fontSize: 11 },
  screenshotImg: { width: 280, height: 210, borderRadius: 12, marginBottom: 4 },
  imgTimePill: {
    position: 'absolute',
    bottom: 8,
    right: 6,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  imgTimeText: { color: '#fff', fontSize: 11 },
  systemWrap: { alignItems: 'center', marginVertical: 4 },
  systemBubble: { borderRadius: 12, paddingHorizontal: 12, paddingVertical: 4 },
  systemText: { fontSize: 13 },
  sentImage: { width: 200, height: 150, borderRadius: 10, marginBottom: 4 },
  actionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
  actionButton: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 14 },
  actionButtonText: { color: '#fff', fontSize: 13, fontWeight: '500' },
});
