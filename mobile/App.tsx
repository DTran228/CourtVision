import { useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import HomeScreen from './screens/HomeScreen';
import PickVideoScreen from './screens/PickVideoScreen';
import ReviewScreen from './screens/ReviewScreen';
import { Connection } from './api';

export default function App() {
  // State is a value React remembers. Updating it redraws the screen.
  const [screen, setScreen] = useState<'home' | 'pick-video' | 'review'>('home');
  const [connection, setConnection] = useState<Connection>({ url: process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.1.10:8000', token: '' });
  const [sessionId, setSessionId] = useState('');
  const [jobId, setJobId] = useState<string>();
  function openSession(id: string) { setSessionId(id); setScreen('review'); }

  return (
    <SafeAreaProvider>
      {/* Keep content clear of the iPhone notch and home indicator. */}
      <SafeAreaView style={styles.container}>
        <StatusBar style="dark" />
        {screen === 'home' ? (
          <HomeScreen connection={connection} setConnection={setConnection} onSession={openSession}
            onJob={id => { setJobId(id); setScreen('pick-video'); }}
            onContinue={() => { setJobId(undefined); setScreen('pick-video'); }} />
        ) : screen === 'review' ? (
          <ReviewScreen connection={connection} id={sessionId} onBack={() => setScreen('home')} />
        ) : (
          <PickVideoScreen connection={connection} initialJobId={jobId} onSession={openSession} onBack={() => setScreen('home')} />
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
});
