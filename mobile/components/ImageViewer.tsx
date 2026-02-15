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
  const baseScale = useRef(1);
  const pinchDist = useRef(0);
  const panX = useRef(0);
  const panY = useRef(0);
  const lastTap = useRef(0);
  const touchCount = useRef(0);

  const reset = useCallback(() => {
    scale.setValue(1);
    translateX.setValue(0);
    translateY.setValue(0);
    baseScale.current = 1;
    panX.current = 0;
    panY.current = 0;
  }, []);

  const dist = (a: any, b: any) => Math.hypot(a.pageX - b.pageX, a.pageY - b.pageY);

  const handleClose = useCallback(() => { reset(); onClose(); }, [onClose, reset]);

  if (!visible) return null;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={handleClose}>
      <View
        style={styles.root}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderTerminationRequest={() => false}
        onResponderTerminate={() => { touchCount.current = 0; pinchDist.current = 0; }}
        onResponderGrant={(e) => {
          const t = e.nativeEvent.touches;
          touchCount.current = t.length;
          if (t.length === 2) pinchDist.current = dist(t[0], t[1]);
        }}
        onResponderMove={(e) => {
          const t = e.nativeEvent.touches;
          touchCount.current = t.length;
          if (t.length === 2 && pinchDist.current > 0) {
            const d = dist(t[0], t[1]);
            const s = Math.max(0.5, Math.min(5, baseScale.current * (d / pinchDist.current)));
            scale.setValue(s);
          } else if (t.length === 1 && baseScale.current > 1) {
            translateX.setValue(panX.current + (t[0].pageX - e.nativeEvent.pageX));
            translateY.setValue(panY.current + (t[0].pageY - e.nativeEvent.pageY));
          }
        }}
        onResponderRelease={(e) => {
          const curScale = (scale as any).__getValue();
          if (touchCount.current >= 2) {
            // pinch ended
            baseScale.current = curScale;
            if (curScale < 1) {
              Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 7 }).start();
              baseScale.current = 1;
            }
            pinchDist.current = 0;
          } else {
            // single finger release
            panX.current = (translateX as any).__getValue();
            panY.current = (translateY as any).__getValue();
            if (curScale <= 1) {
              Animated.parallel([
                Animated.spring(translateX, { toValue: 0, useNativeDriver: true, friction: 7 }),
                Animated.spring(translateY, { toValue: 0, useNativeDriver: true, friction: 7 }),
              ]).start();
              panX.current = 0;
              panY.current = 0;
            }
            // double tap
            const now = Date.now();
            if (now - lastTap.current < 300) {
              if (baseScale.current > 1.5) {
                Animated.parallel([
                  Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 7 }),
                  Animated.spring(translateX, { toValue: 0, useNativeDriver: true, friction: 7 }),
                  Animated.spring(translateY, { toValue: 0, useNativeDriver: true, friction: 7 }),
                ]).start();
                baseScale.current = 1;
                panX.current = 0;
                panY.current = 0;
              } else {
                Animated.spring(scale, { toValue: 2.5, useNativeDriver: true, friction: 7 }).start();
                baseScale.current = 2.5;
              }
              lastTap.current = 0;
            } else {
              lastTap.current = now;
              // single tap — close if not zoomed
              if (baseScale.current <= 1) {
                setTimeout(() => {
                  if (Date.now() - lastTap.current >= 280) handleClose();
                }, 300);
              }
            }
          }
          touchCount.current = 0;
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
  image: { width: SW, height: SH * 0.85 },
  closeBtn: { position: 'absolute', top: 50, right: 20, width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  closeText: { color: '#fff', fontSize: 18 },
});
