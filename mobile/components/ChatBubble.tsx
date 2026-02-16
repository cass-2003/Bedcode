import React, { useEffect, useRef, useState, useCallback } from 'react';
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
import ImageViewer from './ImageViewer';

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
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenUri, setFullscreenUri] = useState('');
  const [imgRatio, setImgRatio] = useState(16 / 9);

  useEffect(() => {
    const uri = imageUri || (imageBase64 ? `data:image/png;base64,${imageBase64}` : '');
    if (uri) {
      Image.getSize(uri, (w, h) => { if (w && h) setImgRatio(w / h); }, () => {});
    }
  }, [imageUri, imageBase64]);

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 150, useNativeDriver: true }).start();
  }, []);

  const handleLongPress = () => {
    Alert.alert('操作', undefined, [
      { text: 'Copy', onPress: () => Clipboard.setStringAsync(text) },
      { text: '取消', style: 'cancel' },
    ]);
  };

  const openImage = (uri: string) => {
    setFullscreenUri(uri);
    setFullscreen(true);
  };

  const time = formatTime(timestamp);

  const imgW = imgRatio >= 1 ? SCREEN_W * 0.75 : SCREEN_W * 0.55;
  const imgStyle = { width: imgW, aspectRatio: imgRatio, borderRadius: 8 };

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
                  style={[styles.actionButton, { backgroundColor: c.actionBg, borderWidth: 1, borderColor: c.actionText }]}
                  onPress={() => onAction?.(a.action || 'qr', a.keys)}
                >
                  <Text style={[styles.actionButtonText, { color: c.actionText }]}>{a.label}</Text>
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

  const hasImage = (isSent && imageUri) || (isScreenshot && imageBase64);

  // Skip empty bubbles
  if (!text && !hasImage && (!actions || actions.length === 0)) return null;

  return (
    <>
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
              hasImage && !text ? styles.imageBubble : undefined,
              hasImage && !text
                ? { borderRadius: 10 }
                : isSent
                ? { borderTopLeftRadius: 12, borderTopRightRadius: 12, borderBottomLeftRadius: 12, borderBottomRightRadius: 4 }
                : { borderTopLeftRadius: 4, borderTopRightRadius: 12, borderBottomLeftRadius: 12, borderBottomRightRadius: 12 },
            ]}
          >
            {(!isSent && !isScreenshot || isPrompt) && showSender !== false && (
              <Text style={[styles.senderName, { color: c.senderColors[0] }]}>Claude</Text>
            )}

            {isSent && imageUri && (
              <Pressable onPress={() => openImage(imageUri)}>
                <Image source={{ uri: imageUri }} style={imgStyle} resizeMode="cover" />
                <View style={styles.imgTimePill}>
                  <Text style={styles.imgTimeText}>{time}{statusEl ? ' ' : ''}{statusEl && (statusIcon[status!] ?? status)}</Text>
                </View>
              </Pressable>
            )}

            {isScreenshot && imageBase64 ? (
              <Pressable onPress={() => openImage(`data:image/png;base64,${imageBase64}`)}>
                <Image
                  source={{ uri: `data:image/png;base64,${imageBase64}` }}
                  style={imgStyle}
                  resizeMode="cover"
                />
                <View style={styles.imgTimePill}>
                  <Text style={styles.imgTimeText}>{time}</Text>
                </View>
              </Pressable>
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
                    style={[styles.actionButton, { backgroundColor: c.actionBg, borderWidth: 1, borderColor: c.actionText }]}
                    onPress={() => onAction?.(a.action || 'qr', a.keys)}
                  >
                    <Text style={[styles.actionButtonText, { color: c.actionText }]}>{a.label}</Text>
                  </Pressable>
                ))}
              </View>
            )}
          </View>
        </Pressable>
      </Animated.View>

      <ImageViewer visible={fullscreen} uri={fullscreenUri} onClose={() => setFullscreen(false)} />
    </>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', marginBottom: 3, paddingHorizontal: 8 },
  bubbleWrap: { maxWidth: SCREEN_W * 0.82 },
  bubble: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 18,
    minWidth: 60,
  },
  imageBubble: { paddingHorizontal: 2, paddingTop: 2, paddingBottom: 2, minWidth: 0, overflow: 'hidden' },
  senderName: { fontSize: 13, fontWeight: '600', marginBottom: 2 },
  text: { fontSize: 15, lineHeight: 20 },
  timeInlineSpacer: { fontSize: 11, color: 'transparent' },
  meta: { flexDirection: 'row', position: 'absolute', bottom: 4, right: 8, alignItems: 'center' },
  time: { fontSize: 10, letterSpacing: 0.2 },
  statusText: { fontSize: 10 },
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
  systemBubble: { borderRadius: 16, paddingHorizontal: 14, paddingVertical: 6 },
  systemText: { fontSize: 13 },
  actionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
  actionButton: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  actionButtonText: { fontSize: 13, fontWeight: '500' },
});
