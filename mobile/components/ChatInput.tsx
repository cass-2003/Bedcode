import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  View,
  TextInput,
  Pressable,
  Image,
  Text,
  Animated,
  FlatList,
  StyleSheet,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

const COMMANDS = [
  { cmd: 'screenshot', icon: '\u{1F4F7}', desc: '截取屏幕' },
  { cmd: 'watch', icon: '\u{1F440}', desc: '开关自动监控' },
  { cmd: 'stop', icon: '\u23F9', desc: '中断 Claude' },
  { cmd: 'grab', icon: '\u{1F504}', desc: '抓取当前状态' },
  { cmd: 'undo', icon: '\u21A9', desc: '撤销上一步' },
  { cmd: 'cost', icon: '\u{1F4B0}', desc: '查看费用' },
  { cmd: 'export', icon: '\u{1F4E4}', desc: '导出对话' },
  { cmd: 'clipboard', icon: '\u{1F4CB}', desc: '查看剪贴板' },
  { cmd: 'clip', icon: '\u{1F4CB}', desc: '剪贴板读写' },
  { cmd: 'windows', icon: '\u{1FA9F}', desc: '窗口列表' },
  { cmd: 'key', icon: '\u2328', desc: '发送按键 (如 /key Enter)' },
  { cmd: 'break', icon: '\u{1F6D1}', desc: '发送 Break' },
  { cmd: 'tpl', icon: '\u{1F4DD}', desc: '模板管理' },
  { cmd: 'alias', icon: '\u{1F517}', desc: '别名管理' },
  { cmd: 'batch', icon: '\u{1F4E6}', desc: '批量发送' },
  { cmd: 'queue', icon: '\u{1F4CB}', desc: '查看队列' },
  { cmd: 'search', icon: '\u{1F50D}', desc: '搜索历史' },
  { cmd: 'history', icon: '\u{1F4DC}', desc: '历史记录' },
  { cmd: 'schedule', icon: '\u23F0', desc: '定时任务' },
  { cmd: 'panel', icon: '\u{1F39B}', desc: '自定义面板' },
];

type Props = {
  onSend: (text: string, imageUri?: string) => void;
  onCommand?: (cmd: string, args: string) => void;
};

export default function ChatInput({ onSend, onCommand }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const [text, setText] = useState('');
  const [imageUris, setImageUris] = useState<string[]>([]);
  const sendScale = useRef(new Animated.Value(0)).current;

  const hasContent = text.trim().length > 0 || imageUris.length > 0;

  const suggestions = useMemo(() => {
    const t = text.trim();
    if (!t.startsWith('/') || imageUris.length > 0) return [];
    const query = t.slice(1).toLowerCase();
    return COMMANDS.filter((c) => c.cmd.startsWith(query));
  }, [text, imageUris.length]);

  useEffect(() => {
    Animated.spring(sendScale, {
      toValue: hasContent ? 1 : 0,
      useNativeDriver: true,
      friction: 8,
    }).start();
  }, [hasContent]);

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      quality: 0.7,
    });
    if (!result.canceled && result.assets.length > 0) {
      setImageUris((prev) => [...prev, ...result.assets.map((a) => a.uri)]);
    }
  };

  const removeImage = (idx: number) => {
    setImageUris((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && imageUris.length === 0) return;

    if (trimmed.startsWith('/') && !imageUris.length && onCommand) {
      const spaceIdx = trimmed.indexOf(' ');
      const cmd = spaceIdx > 0 ? trimmed.slice(1, spaceIdx) : trimmed.slice(1);
      const args = spaceIdx > 0 ? trimmed.slice(spaceIdx + 1).trim() : '';
      onCommand(cmd, args);
      setText('');
      return;
    }

    // Send first image with text; queue remaining images
    onSend(trimmed, imageUris[0]);
    for (let i = 1; i < imageUris.length; i++) {
      onSend('', imageUris[i]);
    }
    setText('');
    setImageUris([]);
  };

  const isLight = theme === 'light';

  return (
    <View style={[styles.container, { backgroundColor: c.inputBar, borderTopColor: c.border }]}>
      {suggestions.length > 0 && (
        <FlatList
          data={suggestions}
          keyExtractor={(item) => item.cmd}
          keyboardShouldPersistTaps="always"
          style={[styles.suggestions, { backgroundColor: c.inputField, borderColor: c.border }]}
          renderItem={({ item }) => (
            <Pressable
              style={styles.sugItem}
              onPress={() => {
                if (onCommand) onCommand(item.cmd, '');
                setText('');
              }}
            >
              <Text style={styles.sugIcon}>{item.icon}</Text>
              <Text style={[styles.sugCmd, { color: c.text }]}>/{item.cmd}</Text>
              <Text style={[styles.sugDesc, { color: c.textSecondary }]}>{item.desc}</Text>
            </Pressable>
          )}
        />
      )}
      {imageUris.length > 0 && (
        <View style={styles.previewRow}>
          {imageUris.map((uri, i) => (
            <View key={uri} style={[styles.previewBorder, { borderColor: c.border }]}>
              <Image source={{ uri }} style={styles.preview} />
              <Pressable onPress={() => removeImage(i)} style={styles.removeBtn}>
                <Text style={styles.removeText}>{'\u2715'}</Text>
              </Pressable>
            </View>
          ))}
        </View>
      )}
      <View style={styles.row}>
        <Pressable onPress={pickImage} style={styles.attachBtn}>
          <Text style={[styles.attachIcon, { color: c.textSecondary }]}>{'\u{1F4CE}'}</Text>
        </Pressable>
        <TextInput
          style={[
            styles.input,
            {
              backgroundColor: c.inputField,
              color: c.text,
              borderWidth: isLight ? 1 : 0,
              borderColor: isLight ? c.border : 'transparent',
            },
          ]}
          placeholder="Message"
          placeholderTextColor={c.textSecondary}
          value={text}
          onChangeText={setText}
          multiline
        />
        <Animated.View style={{ transform: [{ scale: sendScale }], opacity: sendScale }}>
          <Pressable onPress={handleSend} style={[styles.sendBtn, { backgroundColor: c.accent }]}>
            <Text style={[styles.sendIcon, { transform: [{ rotate: '45deg' }] }]}>{'\u2708'}</Text>
          </Pressable>
        </Animated.View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  row: { flexDirection: 'row', alignItems: 'flex-end' },
  attachBtn: { padding: 10, justifyContent: 'center' },
  attachIcon: { fontSize: 22, opacity: 0.7 },
  input: {
    flex: 1,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 11,
    fontSize: 16,
    maxHeight: 120,
    marginHorizontal: 6,
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendIcon: { color: '#fff', fontSize: 18 },
  previewRow: { marginBottom: 6, marginLeft: 46, flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  previewBorder: { borderWidth: 1, borderRadius: 10, padding: 2, alignSelf: 'flex-start' },
  preview: { width: 72, height: 72, borderRadius: 10 },
  removeBtn: {
    position: 'absolute',
    top: -6,
    right: -6,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  suggestions: { maxHeight: 200, borderWidth: 1, borderRadius: 10, marginBottom: 6 },
  sugItem: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 10, gap: 8 },
  sugIcon: { fontSize: 16 },
  sugCmd: { fontSize: 14, fontWeight: '600' },
  sugDesc: { fontSize: 12, flex: 1 },
});
