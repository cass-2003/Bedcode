import React, { useRef } from 'react';
import { StyleSheet, Dimensions, Pressable, Modal, Animated, PanResponder, View, Text } from 'react-native';

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
  const lastScale = useRef(1);
  const lastDist = useRef(0);
  const lastX = useRef(0);
  const lastY = useRef(0);

  const reset = () => {
    scale.setValue(1);
    translateX.setValue(0);
    translateY.setValue(0);
    lastScale.current = 1;
    lastX.current = 0;
    lastY.current = 0;
  };

  const getDistance = (touches: any[]) => {
    const dx = touches[0].pageX - touches[1].pageX;
    const dy = touches[0].pageY - touches[1].pageY;
    return Math.sqrt(dx * dx + dy * dy);
  };

  const panResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (e) => {
      const touches = e.nativeEvent.touches;
      if (touches.length === 2) {
        lastDist.current = getDistance(touches);
      }
    },
    onPanResponderMove: (e, gesture) => {
      const touches = e.nativeEvent.touches;
      if (touches.length === 2) {
        const dist = getDistance(touches);
        if (lastDist.current > 0) {
          const newScale = Math.max(0.5, Math.min(5, lastScale.current * (dist / lastDist.current)));
          scale.setValue(newScale);
        }
      } else if (lastScale.current > 1) {
        translateX.setValue(lastX.current + gesture.dx);
        translateY.setValue(lastY.current + gesture.dy);
      }
    },
    onPanResponderRelease: () => {
      lastScale.current = (scale as any).__getValue();
      if (lastScale.current < 1) {
        Animated.spring(scale, { toValue: 1, useNativeDriver: true }).start();
        lastScale.current = 1;
      }
      lastX.current = (translateX as any).__getValue();
      lastY.current = (translateY as any).__getValue();
      if (lastScale.current <= 1) {
        Animated.parallel([
          Animated.spring(translateX, { toValue: 0, useNativeDriver: true }),
          Animated.spring(translateY, { toValue: 0, useNativeDriver: true }),
        ]).start();
        lastX.current = 0;
        lastY.current = 0;
      }
    },
  })).current;

  const handleClose = () => {
    reset();
    onClose();
  };

  let lastTap = useRef(0);
  const handleTap = () => {
    const now = Date.now();
    if (now - lastTap.current < 300) {
      // double tap
      if (lastScale.current > 1.5) {
        Animated.parallel([
          Animated.spring(scale, { toValue: 1, useNativeDriver: true }),
          Animated.spring(translateX, { toValue: 0, useNativeDriver: true }),
          Animated.spring(translateY, { toValue: 0, useNativeDriver: true }),
        ]).start();
        lastScale.current = 1;
        lastX.current = 0;
        lastY.current = 0;
      } else {
        Animated.spring(scale, { toValue: 2.5, useNativeDriver: true }).start();
        lastScale.current = 2.5;
      }
    }
    lastTap.current = now;
  };

  if (!visible) return null;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={handleClose}>
      <View style={styles.root}>
        <Animated.Image
          source={{ uri }}
          style={[styles.image, {
            transform: [
              { translateX },
              { translateY },
              { scale },
            ],
          }]}
          resizeMode="contain"
          {...panResponder.panHandlers}
          onResponderRelease={handleTap}
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
  image: { width: SW, height: SH * 0.8 },
  closeBtn: { position: 'absolute', top: 50, right: 20, width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' },
  closeText: { color: '#fff', fontSize: 18 },
});
