import React, { useRef, useCallback } from 'react';
import { StyleSheet, Dimensions, Pressable, Modal, Animated, View, Text } from 'react-native';

const { width: SW, height: SH } = Dimensions.get('window');

type Props = {
  visible: boolean;
  uri: string;
  onClose: () => void;
};

export default function ImageViewer({ visible, uri, onClose }: Props) {
  const scale = useRef(new Animated.Value(1)).current;
  const translateX = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(0)).current;

  const cur = useRef({ scale: 1, x: 0, y: 0 });
  const gesture = useRef<'none' | 'pinch' | 'pan'>('none');
  const pinchStart = useRef(0);
  const panStart = useRef({ x: 0, y: 0 });
  const lastTap = useRef(0);

  const reset = useCallback(() => {
    scale.setValue(1);
    translateX.setValue(0);
    translateY.setValue(0);
    cur.current = { scale: 1, x: 0, y: 0 };
    gesture.current = 'none';
  }, []);

  const dist = (t: any) => Math.hypot(t[0].pageX - t[1].pageX, t[0].pageY - t[1].pageY);

  const handleClose = useCallback(() => { reset(); onClose(); }, [onClose, reset]);

  if (!visible) return null;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={handleClose}>
      <View
        style={styles.root}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderTerminationRequest={() => false}
        onResponderGrant={(e) => {
          const t = e.nativeEvent.touches;
          if (t.length === 2) {
            gesture.current = 'pinch';
            pinchStart.current = dist(t);
          } else if (t.length === 1) {
            gesture.current = 'pan';
            panStart.current = { x: t[0].pageX, y: t[0].pageY };
          }
        }}
        onResponderMove={(e) => {
          const t = e.nativeEvent.touches;
          if (t.length === 2) {
            if (gesture.current !== 'pinch') {
              gesture.current = 'pinch';
              pinchStart.current = dist(t);
            }
            const d = dist(t);
            const s = Math.max(0.5, Math.min(5, cur.current.scale * (d / pinchStart.current)));
            scale.setValue(s);
          } else if (t.length === 1 && gesture.current === 'pan' && cur.current.scale > 1) {
            const dx = t[0].pageX - panStart.current.x;
            const dy = t[0].pageY - panStart.current.y;
            translateX.setValue(cur.current.x + dx);
            translateY.setValue(cur.current.y + dy);
          }
        }}
        onResponderRelease={(e) => {
          const t = e.nativeEvent.touches;
          // Still have fingers down — update state for remaining gesture
          if (t.length >= 2) {
            pinchStart.current = dist(t);
            return;
          }
          if (t.length === 1) {
            // One finger lifted from pinch — save scale, switch to pan
            if (gesture.current === 'pinch') {
              const d = dist([t[0], { pageX: e.nativeEvent.pageX, pageY: e.nativeEvent.pageY }]);
              const s = Math.max(0.5, Math.min(5, cur.current.scale * (d / (pinchStart.current || 1))));
              cur.current.scale = s < 1 ? 1 : s;
              if (s < 1) {
                Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 7 }).start();
              }
              gesture.current = 'pan';
              panStart.current = { x: t[0].pageX, y: t[0].pageY };
            }
            return;
          }

          // All fingers up
          if (gesture.current === 'pinch') {
            // Read final scale from ratio
            // Already saved above when going 2→1, but handle 2→0 directly
            const raw = (scale as any)._value ?? cur.current.scale;
            cur.current.scale = raw < 1 ? 1 : raw;
            if (raw < 1) {
              Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 7 }).start();
              cur.current.scale = 1;
            }
          } else if (gesture.current === 'pan') {
            const raw = {
              x: (translateX as any)._value ?? cur.current.x,
              y: (translateY as any)._value ?? cur.current.y,
            };
            cur.current.x = raw.x;
            cur.current.y = raw.y;
            if (cur.current.scale <= 1) {
              Animated.parallel([
                Animated.spring(translateX, { toValue: 0, useNativeDriver: true, friction: 7 }),
                Animated.spring(translateY, { toValue: 0, useNativeDriver: true, friction: 7 }),
              ]).start();
              cur.current.x = 0;
              cur.current.y = 0;
            }
          }

          // Double tap
          const now = Date.now();
          if (now - lastTap.current < 300) {
            if (cur.current.scale > 1.5) {
              Animated.parallel([
                Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 7 }),
                Animated.spring(translateX, { toValue: 0, useNativeDriver: true, friction: 7 }),
                Animated.spring(translateY, { toValue: 0, useNativeDriver: true, friction: 7 }),
              ]).start();
              cur.current = { scale: 1, x: 0, y: 0 };
            } else {
              Animated.spring(scale, { toValue: 2.5, useNativeDriver: true, friction: 7 }).start();
              cur.current.scale = 2.5;
            }
            lastTap.current = 0;
          } else {
            lastTap.current = now;
            if (cur.current.scale <= 1 && gesture.current !== 'pinch') {
              setTimeout(() => {
                if (Date.now() - lastTap.current >= 280) handleClose();
              }, 300);
            }
          }
          gesture.current = 'none';
        }}
      >
        <Animated.Image
          source={{ uri }}
          style={[styles.image, {
            transform: [{ translateX }, { translateY }, { scale }],
          }]}
          resizeMode="contain"
        />
        <Pressable style={styles.closeBtn} onPress={handleClose}>
          <Text style={styles.closeText}>{'\u2715'}</Text>
        </Pressable>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: 'rgba(0,0,0,0.95)', justifyContent: 'center', alignItems: 'center' },
  image: { width: SW, height: SH },
  closeBtn: { position: 'absolute', top: 50, right: 20, width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  closeText: { color: '#fff', fontSize: 18 },
});
