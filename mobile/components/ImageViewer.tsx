import React from 'react';
import { StyleSheet, Dimensions, Pressable, Modal } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from 'react-native-reanimated';
import { GestureDetector, Gesture, GestureHandlerRootView } from 'react-native-gesture-handler';

const { width: SW, height: SH } = Dimensions.get('window');

type Props = {
  visible: boolean;
  uri: string;
  onClose: () => void;
};

export default function ImageViewer({ visible, uri, onClose }: Props) {
  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedX = useSharedValue(0);
  const savedY = useSharedValue(0);

  const pinch = Gesture.Pinch()
    .onUpdate((e) => { scale.value = savedScale.value * e.scale; })
    .onEnd(() => {
      if (scale.value < 1) { scale.value = withTiming(1); savedScale.value = 1; }
      else { savedScale.value = scale.value; }
    });

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      translateX.value = savedX.value + e.translationX;
      translateY.value = savedY.value + e.translationY;
    })
    .onEnd(() => {
      if (scale.value <= 1) {
        translateX.value = withTiming(0);
        translateY.value = withTiming(0);
        savedX.value = 0;
        savedY.value = 0;
      } else {
        savedX.value = translateX.value;
        savedY.value = translateY.value;
      }
    });

  const doubleTap = Gesture.Tap().numberOfTaps(2).onEnd(() => {
    if (scale.value > 1) {
      scale.value = withTiming(1);
      translateX.value = withTiming(0);
      translateY.value = withTiming(0);
      savedScale.value = 1;
      savedX.value = 0;
      savedY.value = 0;
    } else {
      scale.value = withTiming(2.5);
      savedScale.value = 2.5;
    }
  });

  const composed = Gesture.Simultaneous(pinch, pan, doubleTap);

  const animStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
  }));

  const handleClose = () => {
    scale.value = 1;
    savedScale.value = 1;
    translateX.value = 0;
    translateY.value = 0;
    savedX.value = 0;
    savedY.value = 0;
    onClose();
  };

  if (!visible) return null;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={handleClose}>
      <GestureHandlerRootView style={styles.root}>
        <Pressable style={styles.closeZone} onPress={handleClose} />
        <GestureDetector gesture={composed}>
          <Animated.Image
            source={{ uri }}
            style={[styles.image, animStyle]}
            resizeMode="contain"
          />
        </GestureDetector>
        <Pressable style={styles.closeBtn} onPress={handleClose}>
          <Animated.Text style={styles.closeText}>{'\u2715'}</Animated.Text>
        </Pressable>
      </GestureHandlerRootView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: 'rgba(0,0,0,0.95)', justifyContent: 'center', alignItems: 'center' },
  closeZone: { ...StyleSheet.absoluteFillObject },
  image: { width: SW, height: SH * 0.8 },
  closeBtn: { position: 'absolute', top: 50, right: 20, width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' },
  closeText: { color: '#fff', fontSize: 18 },
});
