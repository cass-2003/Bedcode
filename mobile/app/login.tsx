import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useChatStore } from '../stores/chatStore';
import { Colors } from '../constants/theme';

export default function LoginScreen() {
  const { host: savedHost, setAuth } = useChatStore();
  const [host, setHost] = useState(savedHost || '');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const c = Colors.dark;

  const handleConnect = async () => {
    const h = host.trim().replace(/\/+$/, '');
    const t = token.trim();
    if (!h || !t) return Alert.alert('错误', '请填写所有字段');
    setLoading(true);
    try {
      const res = await fetch(`${h}/api/health`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAuth(h, t);
      router.replace('/(tabs)');
    } catch (e: any) {
      Alert.alert('连接失败', e.message || '无法连接到服务器');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: c.background }]}>
      <Text style={[styles.logo, { color: c.accent }]}>BedCode</Text>
      <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.border }]}>
        <Text style={[styles.label, { color: c.textSecondary }]}>服务器地址</Text>
        <TextInput
          style={[styles.input, { backgroundColor: c.inputField, color: c.text, borderColor: c.border }]}
          value={host}
          onChangeText={setHost}
          placeholder="http://192.168.1.100:8080"
          placeholderTextColor={c.textSecondary}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <Text style={[styles.label, { color: c.textSecondary }]}>API Token</Text>
        <TextInput
          style={[styles.input, { backgroundColor: c.inputField, color: c.text, borderColor: c.border }]}
          value={token}
          onChangeText={setToken}
          placeholder="输入 Token"
          placeholderTextColor={c.textSecondary}
          secureTextEntry
          autoCapitalize="none"
        />
        <TouchableOpacity
          style={[styles.button, { backgroundColor: c.accent }]}
          onPress={handleConnect}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>连接</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  logo: { fontSize: 32, fontWeight: '700', marginBottom: 32 },
  card: { width: '100%', maxWidth: 400, borderRadius: 12, borderWidth: 1, padding: 20 },
  label: { fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: { height: 44, borderRadius: 8, borderWidth: 1, paddingHorizontal: 12, fontSize: 15 },
  button: { height: 46, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 24 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
