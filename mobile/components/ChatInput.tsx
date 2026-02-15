import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  TextInput,
  Pressable,
  Image,
  Text,
  Animated,
  StyleSheet,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../constants/theme';
import { useChatStore } from '../stores/chatStore';

type Props = {
  onSend: (text: string, imageUri?: string) => void;
};

export default function ChatInput({ onSend }: Props) {
  const theme = useChatStore((s) => s.theme);
  const c = Colors[theme];
  const [text, setText] = useState('');
  const [imageUris, setImageUris] = useState<string[]>([]);
  const sendScale = useRef(new Animated.Value(0)).current;

  const hasContent = text.trim().length > 0 || imageUris.length > 0;

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
    <View style={[styles.container, { backgroundColor: c.inputBar }]}>
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
            <Text style={styles.sendIcon}>{'\u279C'}</Text>
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 3,
  },
  row: { flexDirection: 'row', alignItems: 'flex-end' },
  attachBtn: { padding: 10, justifyContent: 'center' },
  attachIcon: { fontSize: 24 },
  input: {
    flex: 1,
    borderRadius: 21,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 16,
    maxHeight: 120,
    marginHorizontal: 6,
  },
  sendBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendIcon: { color: '#fff', fontSize: 18 },
  previewRow: { marginBottom: 6, marginLeft: 46, flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  previewBorder: { borderWidth: 1, borderRadius: 10, padding: 2, alignSelf: 'flex-start' },
  preview: { width: 64, height: 64, borderRadius: 8 },
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
});
