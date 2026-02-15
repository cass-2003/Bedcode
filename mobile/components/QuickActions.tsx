import React from 'react';
import {
  View,
  Text,
  Pressable,
  Modal,
  Animated,
  StyleSheet,
} from 'react-native';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = {
  onAction: (action: string) => void;
  visible: boolean;
  onClose: () => void;
};

const actions = [
  { icon: '\u{1F4F8}', label: '截屏', action: 'screenshot' },
  { icon: '\u26D4', label: '中断', action: 'interrupt' },
  { icon: '\u21A9', label: '撤销', action: 'undo' },
  { icon: '\u{1F4CB}', label: 'Grab', action: 'grab' },
  { icon: '\u{1FA9F}', label: '窗口', action: 'window' },
  { icon: '\u{1F4B0}', label: '费用', action: 'cost' },
];

export default function QuickActions({ onAction, visible, onClose }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const slideAnim = React.useRef(new Animated.Value(300)).current;

  React.useEffect(() => {
    Animated.spring(slideAnim, {
      toValue: visible ? 0 : 300,
      useNativeDriver: true,
      friction: 9,
      tension: 65,
    }).start();
  }, [visible]);

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Animated.View
          style={[
            styles.sheet,
            { backgroundColor: c.surface, transform: [{ translateY: slideAnim }] },
          ]}
        >
          <View style={styles.handle} />
          <View style={styles.grid}>
            {actions.map((a) => (
              <Pressable
                key={a.action}
                style={styles.item}
                onPress={() => { onAction(a.action); onClose(); }}
              >
                <View style={[styles.iconCircle, { backgroundColor: c.accent }]}>
                  <Text style={styles.icon}>{a.icon}</Text>
                </View>
                <Text style={[styles.label, { color: c.textSecondary }]}>{a.label}</Text>
              </Pressable>
            ))}
          </View>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { borderTopLeftRadius: 14, borderTopRightRadius: 14, paddingTop: 8, paddingBottom: 36, paddingHorizontal: 16 },
  handle: { width: 36, height: 4, borderRadius: 2, backgroundColor: '#8E8E93', alignSelf: 'center', marginBottom: 16 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-start' },
  item: { width: '25%', alignItems: 'center', marginBottom: 16 },
  iconCircle: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  icon: { fontSize: 22, color: '#fff' },
  label: { fontSize: 12, marginTop: 6 },
});
